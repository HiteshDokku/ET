"""
NEWS SERVICE — LLM Heuristic Ranker

Replaced TF-IDF/Cosine Similarity with an LLM-based ranking system for
higher accuracy and reduced latency. The LLM understands context, nuance,
and user intent far better than keyword math.

The ranker sends article titles/summaries + user profile to ask_llm_fast
and receives back a curated, ranked list with matched_interest assignments
and reason_for_selection explanations — all driven by AI reasoning.
"""

import feedparser
import json
import logging
from datetime import datetime
from dateutil import parser as dateparser
from typing import List, Dict

from app.intel.llm_client import ask_llm_fast

logger = logging.getLogger(__name__)

# Google News RSS base URL
GOOGLE_RSS_BASE = "https://news.google.com/rss/search?hl=en-IN&gl=IN&ceid=IN:en&q="

ET_RSS_FEEDS = {
    "markets":    GOOGLE_RSS_BASE + "stock+market+India+NSE+BSE",
    "tech":       GOOGLE_RSS_BASE + "technology+AI+India",
    "startups":   GOOGLE_RSS_BASE + "startup+funding+India+venture+capital",
    "finance":    GOOGLE_RSS_BASE + "Indian+economy+finance+RBI",
    "healthcare": GOOGLE_RSS_BASE + "healthcare+pharma+biotech+India",
    "crypto":     GOOGLE_RSS_BASE + "cryptocurrency+bitcoin+blockchain+India",
    "general":    GOOGLE_RSS_BASE + "India+business+news",
}


# ═══════════════════════════════════════════════════════════════
#  LLM RANKING PROMPT
# ═══════════════════════════════════════════════════════════════

LLM_RANKER_SYSTEM = """You are an Expert News Curator for a personalized financial/tech news dashboard.

Your job is to select and rank the most relevant articles for a specific user based on their profile.

RULES:
1. Return EXACTLY the number of articles requested (or fewer if not enough qualify).
2. EVERY interest listed by the user MUST have at least 1-2 representative articles.
3. For 'Advanced' users: prioritize technical depth, market analysis, data-driven pieces.
4. For 'Beginner' users: prioritize accessible summaries, explainers, big-picture stories.
5. For 'Intermediate' users: balance depth and accessibility.
6. Assign the most accurate 'matched_interest' — the user interest that BEST explains why this article was selected.
7. Provide a brief 'reason' explaining your selection logic.

OUTPUT FORMAT — return valid JSON:
{
  "ranked_articles": [
    {
      "id": "article_temp_id",
      "matched_interest": "the user interest this article serves",
      "relevance_score": 0.95,
      "reason": "brief reason for selection"
    }
  ]
}

Score articles from 0.0 to 1.0 based on:
- Direct relevance to user's specific interests (0.4 weight)
- Appropriate complexity for user's level (0.2 weight)  
- Recency and newsworthiness (0.2 weight)
- Actionability for user's role (0.2 weight)
"""


def parse_date(entry) -> datetime:
    """Safely parse publish date from RSS feed entry."""
    try:
        if hasattr(entry, "published"):
            return dateparser.parse(entry.published)
    except Exception:
        pass
    return datetime.utcnow()


async def fetch_all_feeds() -> List[Dict]:
    """
    Fetch articles from all RSS feeds.
    No keyword tagging — LLM ranking handles relevance.
    """
    all_articles = []

    for feed_name, feed_url in ET_RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:15]:
                article = {
                    "title":     getattr(entry, "title",   ""),
                    "summary":   getattr(entry, "summary", ""),
                    "url":       getattr(entry, "link",    ""),
                    "source": getattr(entry, "source", {}).get("title", feed_name.capitalize()) 
                        if hasattr(getattr(entry, "source", None), "get") 
                        else feed_name.capitalize(),
                    "category":  feed_name,
                    "tags":      [feed_name],
                    "published": parse_date(entry),
                }

                if article["title"] and article["url"]:
                    all_articles.append(article)

        except Exception as e:
            print(f"⚠️  Failed to fetch {feed_name} feed: {e}")
            continue

    print(f"✅  Fetched {len(all_articles)} articles from RSS feeds")
    return all_articles


async def llm_rank_articles(
    articles: List[Dict],
    profile:  Dict,
    top_n:    int = 15,
    language: str = "English",
) -> List[Dict]:
    """
    LLM Heuristic Ranker — replaces TF-IDF/Cosine Similarity.

    Sends article titles + user profile to ask_llm_fast.
    The LLM returns a ranked list with matched_interest assignments
    and reason_for_selection, all driven by AI reasoning rather than
    keyword math.

    This is faster (one LLM call vs N TF-IDF passes) and more accurate
    (understands context, not just word overlap).
    """
    if not articles:
        return []

    interests = profile.get("interests", [])
    role      = profile.get("role", "reader")
    level     = profile.get("level", "beginner")

    if not interests:
        return articles[:top_n]

    # ── Build article catalog for the LLM ────────────────────
    # Give each article a temp_id if it doesn't have one
    import uuid
    for art in articles:
        if "temp_id" not in art:
            art["temp_id"] = str(uuid.uuid4())

    # Limit to 30 articles to keep the prompt manageable
    candidate_pool = articles[:30]

    article_catalog = "\n".join([
        f"[{art['temp_id'][:8]}] {art.get('title', 'Untitled')} "
        f"| Source: {art.get('source', '?')} "
        f"| Query: {art.get('query_used', '?')}"
        for art in candidate_pool
    ])

    # ── Build the ranking prompt ─────────────────────────────
    user_prompt = f"""TASK: Rank the following articles for this user.

USER PROFILE:
- Role: {role}
- Expertise Level: {level}
- Interests: {', '.join(interests)}

ARTICLES TO RANK ({len(candidate_pool)} candidates):
{article_catalog}

Select the {top_n} best articles based on these interests: {', '.join(interests)}.
Ensure EVERY interest ({', '.join(interests)}) has at least 1-2 representative articles.
Use the article ID (first 8 chars shown in brackets) as the 'id' field."""

    print(f"\n🧠 LLM Ranker: scoring {len(candidate_pool)} articles for "
          f"role={role}, level={level}, interests={interests}")

    # ── Call the LLM ─────────────────────────────────────────
    try:
        lang = profile.get("preferred_language", "English")
        result = await ask_llm_fast(LLM_RANKER_SYSTEM, user_prompt, language=lang)
        ranked_list = result.get("ranked_articles", [])
    except Exception as e:
        logger.error(f"❌ LLM ranking failed: {e} — falling back to position-based")
        # Fallback: return articles as-is with basic metadata
        return _position_fallback(articles, interests, top_n)

    if not ranked_list:
        logger.warning("⚠️ LLM returned empty ranking — using position fallback")
        return _position_fallback(articles, interests, top_n)

    # ── Map LLM results back to full article dicts ───────────
    # Build lookup by temp_id prefix (LLM sees first 8 chars)
    id_lookup = {}
    for art in candidate_pool:
        full_id = art["temp_id"]
        id_lookup[full_id] = art
        id_lookup[full_id[:8]] = art  # also index by short ID

    selected = []
    seen_urls = set()

    for ranked in ranked_list[:top_n]:
        art_id = ranked.get("id", "")
        article = id_lookup.get(art_id)

        if not article:
            # Try fuzzy match on short ID
            for key, val in id_lookup.items():
                if art_id in key or key in art_id:
                    article = val
                    break

        if not article:
            continue

        url = article.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Merge LLM ranking data into the article
        enriched = {
            **article,
            "matched_interest":     ranked.get("matched_interest", interests[0] if interests else ""),
            "relevance_score":      ranked.get("relevance_score", 0.8),
            "reason_for_selection": ranked.get("reason", ""),
        }
        selected.append(enriched)

    # ── Ensure interest coverage ─────────────────────────────
    # Check if any interest is completely missing
    covered_interests = set(a.get("matched_interest", "") for a in selected)
    missing = [i for i in interests if i not in covered_interests]

    if missing and len(selected) < top_n:
        # Try to fill from remaining articles
        for art in candidate_pool:
            if len(selected) >= top_n:
                break
            url = art.get("url", "")
            if url in seen_urls:
                continue

            query = art.get("query_used", "").lower()
            title = art.get("title", "").lower()
            for mi in missing:
                if any(word in query or word in title
                       for word in mi.lower().split() if len(word) > 2):
                    art_copy = {
                        **art,
                        "matched_interest": mi,
                        "relevance_score": 0.6,
                        "reason_for_selection": f"Added to ensure coverage of '{mi}'",
                    }
                    selected.append(art_copy)
                    seen_urls.add(url)
                    missing.remove(mi)
                    break

    # ── Log summary ──────────────────────────────────────────
    interest_counts = {}
    for a in selected:
        mi = a.get("matched_interest", "?")
        interest_counts[mi] = interest_counts.get(mi, 0) + 1

    print(f"🎯 LLM Ranked: {len(selected)} articles (from {len(candidate_pool)} candidates)")
    print(f"   Distribution: {interest_counts}")
    if selected:
        scores = [a.get("relevance_score", 0) for a in selected]
        print(f"   Score range: {min(scores):.2f} – {max(scores):.2f}")

    return selected


def _position_fallback(
    articles: List[Dict],
    interests: List[str],
    top_n: int,
) -> List[Dict]:
    """Simple position-based fallback when LLM ranking fails.

    Distributes articles round-robin across interests based on
    query_used keyword matching.
    """
    result = []
    seen_urls = set()

    for interest in interests:
        count = 0
        target = max(2, top_n // max(len(interests), 1))
        for art in articles:
            if count >= target:
                break
            url = art.get("url", "")
            if url in seen_urls:
                continue
            query = art.get("query_used", "").lower()
            title = art.get("title", "").lower()
            if any(word in query or word in title
                   for word in interest.lower().split() if len(word) > 2):
                result.append({
                    **art,
                    "matched_interest": interest,
                    "relevance_score": 0.5,
                    "reason_for_selection": "Position-based fallback",
                })
                seen_urls.add(url)
                count += 1

    # Fill remaining slots
    for art in articles:
        if len(result) >= top_n:
            break
        url = art.get("url", "")
        if url not in seen_urls:
            result.append({
                **art,
                "matched_interest": interests[0] if interests else "",
                "relevance_score": 0.3,
                "reason_for_selection": "Fill slot",
            })
            seen_urls.add(url)

    return result[:top_n]


# ═══════════════════════════════════════════════════════════════
#  DEPRECATED — kept for backward compatibility
# ═══════════════════════════════════════════════════════════════

def rank_articles_for_user(
    articles: List[Dict],
    profile:  Dict,
    top_n:    int = 15,
) -> List[Dict]:
    """DEPRECATED: Use llm_rank_articles() instead.

    This is a sync wrapper that cannot call the async LLM ranker.
    Kept only for backward compatibility — returns a simple
    position-based ranking.
    """
    logger.warning("⚠️ rank_articles_for_user is DEPRECATED — use llm_rank_articles()")
    interests = profile.get("interests", [])
    return _position_fallback(articles, interests, top_n)