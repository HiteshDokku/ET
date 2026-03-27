"""Extract events, entities, and sentiment from a single article."""

from services.llm_client import ask_llm

SYSTEM_PROMPT = """You are an expert news analyst. Extract key events from the given article.
Return a JSON object with this exact structure:
{
  "events": [
    {
      "title": "Short event title",
      "date": "YYYY-MM-DD or 'Unknown'",
      "summary": "2-3 sentence summary of the event",
      "sentiment": "positive" | "negative" | "neutral",
      "entities": ["Person/Company/Org mentioned"]
    }
  ],
  "stance": "One sentence describing the article's overall viewpoint or stance on the topic"
}
Extract ALL distinct events. Be precise with dates. Identify all named entities (people, companies, organizations)."""


async def extract_events(article_id: str, article_title: str, article_content: str) -> dict:
    """Extract events from a single article, returning parsed JSON with article_id attached."""
    user_prompt = f"Article Title: {article_title}\n\nArticle Content:\n{article_content}"
    result = await ask_llm(SYSTEM_PROMPT, user_prompt)

    # Attach source article ID to each event
    for event in result.get("events", []):
        event["source_articles"] = [article_id]

    result["article_id"] = article_id
    return result
