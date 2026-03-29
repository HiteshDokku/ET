"""Orchestrates the full story arc analysis pipeline."""

import asyncio
import logging
import uuid
from app.models.intel import (
    StoryRequest, StoryArcResponse, TimelineEvent,
    KeyPlayer, SentimentOverview, ContrarianInsights,
)
from app.intel.event_extractor import extract_events
from app.intel.contrarian_detector import detect_contrarian
from app.intel.prediction_engine import generate_predictions

logger = logging.getLogger(__name__)


async def analyze_story(request: StoryRequest) -> StoryArcResponse:
    """Run full pipeline and return structured StoryArcResponse.

    Respects request.language — all LLM-generated text (event titles,
    summaries, stances, contrarian insights, predictions) will be
    produced in the requested language.
    """
    language = request.language or "English"

    extraction_results = []
    for a in request.articles:
        try:
            result = await extract_events(a.id, a.title, a.content, language=language)
            extraction_results.append(result)
        except Exception as exc:
            logger.warning(
                f"⚠️  Skipping article '{a.title}' — extraction failed: "
                f"{type(exc).__name__}: {exc}"
            )
        await asyncio.sleep(2.0)

    all_events: list[TimelineEvent] = []
    all_entities: set[str] = set()
    all_stances: list[str] = []
    sentiment_trend: list[str] = []

    for result in extraction_results:
        stance = result.get("stance", "")
        if stance:
            all_stances.append(stance)

        for evt in result.get("events", []):
            event_id = f"evt-{uuid.uuid4().hex[:8]}"
            sentiment = evt.get("sentiment", "neutral")
            entities = evt.get("entities", [])

            all_entities.update(entities)
            sentiment_trend.append(sentiment)

            all_events.append(TimelineEvent(
                event_id=event_id,
                title=evt.get("title", "Untitled Event"),
                date=evt.get("date", "Unknown"),
                summary=evt.get("summary", ""),
                sentiment=sentiment,
                entities=entities,
                source_articles=evt.get("source_articles", []),
                stance=stance,
            ))

    all_events.sort(key=lambda e: e.date if e.date != "Unknown" else "9999-12-31")

    key_players = [
        KeyPlayer(name=entity, role="Mentioned Entity")
        for entity in sorted(all_entities)
    ]

    pos = sentiment_trend.count("positive")
    neg = sentiment_trend.count("negative")
    neu = sentiment_trend.count("neutral")

    if pos > neg and pos > neu:
        overall = "positive"
    elif neg > pos and neg > neu:
        overall = "negative"
    elif pos == neg and pos > 0:
        overall = "mixed"
    else:
        overall = "neutral"

    sentiment_overview = SentimentOverview(trend=sentiment_trend, overall=overall)

    events_summary = "\n".join(
        f"- [{e.date}] {e.title}: {e.summary}" for e in all_events
    )
    # Language-aware summary templates
    _SUMMARY_TEMPLATES = {
        "english": "Analysis of '{topic}' across {articles} articles. Found {events} events involving {entities} entities. Overall sentiment: {sentiment}.",
        "hindi": "'{topic}' का विश्लेषण {articles} लेखों में किया गया। {events} घटनाएं और {entities} संस्थाएं पाई गईं। समग्र भावना: {sentiment}।",
        "marathi": "'{topic}' चे {articles} लेखांमध्ये विश्लेषण केले. {events} घटना आणि {entities} संस्था आढळल्या. एकूण भावना: {sentiment}.",
        "telugu": "'{topic}' విశ్లేషణ {articles} కథనాలలో జరిగింది. {events} సంఘటనలు మరియు {entities} సంస్థలు కనుగొనబడ్డాయి. మొత్తం భావన: {sentiment}.",
        "kannada": "'{topic}' ವಿಶ್ಲೇಷಣೆ {articles} ಲೇಖನಗಳಲ್ಲಿ ನಡೆಯಿತು. {events} ಘಟನೆಗಳು ಮತ್ತು {entities} ಸಂಸ್ಥೆಗಳು ಕಂಡುಬಂದವು. ಒಟ್ಟಾರೆ ಭಾವನೆ: {sentiment}.",
    }
    tpl = _SUMMARY_TEMPLATES.get(language.lower(), _SUMMARY_TEMPLATES["english"])
    story_summary = tpl.format(
        topic=request.topic,
        articles=len(request.articles),
        events=len(all_events),
        entities=len(all_entities),
        sentiment=overall,
    )

    if all_stances:
        contrarian_result = await detect_contrarian(request.topic, all_stances, language=language)
        await asyncio.sleep(2.0)
    else:
        contrarian_result = {"mainstream": "No stances available", "contrarian": []}

    predictions = await generate_predictions(request.topic, story_summary, events_summary, language=language)

    contrarian_insights = ContrarianInsights(
        mainstream=contrarian_result.get("mainstream", ""),
        contrarian=contrarian_result.get("contrarian", []),
    )

    return StoryArcResponse(
        story_summary=story_summary,
        timeline=all_events,
        key_players=key_players,
        sentiment_overview=sentiment_overview,
        contrarian_insights=contrarian_insights,
        what_to_watch=predictions,
    )
