"""Orchestrates the full analysis pipeline: extract → aggregate → contrarian → predict."""

import asyncio
import uuid
from models import (
    StoryRequest, StoryArcResponse, TimelineEvent,
    KeyPlayer, SentimentOverview, ContrarianInsights,
)
from services.event_extractor import extract_events
from services.contrarian_detector import detect_contrarian
from services.prediction_engine import generate_predictions


async def analyze_story(request: StoryRequest) -> StoryArcResponse:
    """Run full pipeline and return structured StoryArcResponse."""

    # ── 1. Extract events from each article sequentially to avoid rate limits ──────
    extraction_results = []
    for a in request.articles:
        result = await extract_events(a.id, a.title, a.content)
        extraction_results.append(result)
        # Small delay to prevent hitting API rate limits
        await asyncio.sleep(2.0)

    # ── 2. Aggregate events, entities, stances ────────────────
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

    # Sort events chronologically (Unknown dates go to the end)
    all_events.sort(key=lambda e: e.date if e.date != "Unknown" else "9999-12-31")

    # ── 3. Build key players list ─────────────────────────────
    key_players = [
        KeyPlayer(name=entity, role="Mentioned Entity")
        for entity in sorted(all_entities)
    ]

    # ── 4. Compute overall sentiment ─────────────────────────
    pos = sentiment_trend.count("positive")
    neg = sentiment_trend.count("negative")
    neu = sentiment_trend.count("neutral")
    total = len(sentiment_trend) or 1

    if pos > neg and pos > neu:
        overall = "positive"
    elif neg > pos and neg > neu:
        overall = "negative"
    elif pos == neg and pos > 0:
        overall = "mixed"
    else:
        overall = "neutral"

    sentiment_overview = SentimentOverview(
        trend=sentiment_trend,
        overall=overall,
    )

    # ── 5. Build story summary for downstream tasks ───────────
    events_summary = "\n".join(
        f"- [{e.date}] {e.title}: {e.summary}" for e in all_events
    )
    story_summary = (
        f"Analysis of '{request.topic}' across {len(request.articles)} articles. "
        f"Found {len(all_events)} events involving {len(all_entities)} entities. "
        f"Overall sentiment: {overall}."
    )

    # ── 6. Run contrarian detection and prediction sequentially ─
    if all_stances:
        contrarian_result = await detect_contrarian(request.topic, all_stances)
        await asyncio.sleep(2.0)  # Delay between API calls
    else:
        contrarian_result = {"mainstream": "No stances available", "contrarian": []}

    predictions = await generate_predictions(request.topic, story_summary, events_summary)

    contrarian_insights = ContrarianInsights(
        mainstream=contrarian_result.get("mainstream", ""),
        contrarian=contrarian_result.get("contrarian", []),
    )

    # ── 7. Assemble final response ────────────────────────────
    return StoryArcResponse(
        story_summary=story_summary,
        timeline=all_events,
        key_players=key_players,
        sentiment_overview=sentiment_overview,
        contrarian_insights=contrarian_insights,
        what_to_watch=predictions,
    )
