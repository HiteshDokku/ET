"""
Agent Orchestrator — Real-time Agentic Dashboard Feed

Pipeline:
 1. Check Redis feed:{user_id} for a FRESH cached feed (5 min grace)
    → If valid, return immediately (prevents rapid-refresh hammering)
 2. Otherwise, ALWAYS run the PersonalizedIntelAgent:
    → Generates queries from ALL user interests
    → Fetches Google News RSS in real-time
    → LLM evaluates relevance + complexity
    → Gap analysis across interests → re-iterates if needed
    → **LLM Final Ranking** (replaces TF-IDF — AI assigns matched_interest)
 3. Rewrite each article with role-appropriate AI personalization
 4. Cache result in Redis feed:{user_id} (5 min TTL)
 5. Return 15 articles covering all user interests
"""

import json
import asyncio
from typing import List, Dict

from app.services.redis_service import (
    get_user_profile,
    get_cached_feed,
    cache_feed,
)
from app.services.news_service import llm_rank_articles
from app.services.ai_service import rewrite_article_for_user
from app.config import settings

# Short-lived grace period to prevent hammer-refresh (5 minutes)
FEED_GRACE_TTL = 300


async def build_personalized_feed(user_id: int, redis_client) -> List[Dict]:
    """
    Build a real-time personalized feed for the Dashboard.

    ALWAYS prioritizes a fresh agent scrape over stale cache.
    Only returns cached data during the 5-minute grace window
    to prevent excessive LLM / RSS calls on rapid refreshes.

    Ranking is now 100% LLM-driven — no TF-IDF or cosine similarity.
    """
    print(f"\n🤖 Orchestrator: Building feed for user {user_id}")

    # ── Step 1: Load user profile & Enforce Interests ─────────
    profile = get_user_profile(user_id)
    if not profile:
        print(f"⚠️  No profile found for user {user_id} — using default")
        profile = {
            "role": "student",
            "interests": [],
            "level": "beginner",
            "engagement": {},
        }

    interests = profile.get("interests", [])
    print(f"👤 Profile loaded: role={profile['role']}, "
          f"interests={interests}, level={profile.get('level', 'beginner')}")

    if not interests:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="User must complete profile setup with interests before a personalized feed can be generated."
        )

    # ── Step 2: Grace-period cache check ──────────────────────
    cached = get_cached_feed(user_id)
    if cached:
        print(f"⚡ Grace cache hit — returning cached feed for user {user_id} "
              f"(TTL: {redis_client.ttl(f'feed:{user_id}')}s remaining)")
        return cached

    # ── Step 3: Run PersonalizedIntelAgent ─────────────────────
    print("🧠 Launching PersonalizedIntelAgent for real-time scraping...")
    agent_articles = await _run_agent(profile)

    if not agent_articles:
        print(f"⚠️  Agent returned no articles for user {user_id}")
        cache_feed(user_id, [], ttl_seconds=60)
        return []

    print(f"📦 Agent returned {len(agent_articles)} curated articles")

    # ── Step 4: LLM Heuristic Ranking ─────────────────────────
    # The agent already does an LLM ranking pass internally.
    # But if we got raw (un-ranked) articles, run the service-level ranker.
    if not any(a.get("reason_for_selection") for a in agent_articles):
        print("🧠 Running LLM Heuristic Ranker on agent output...")
        ranked = await llm_rank_articles(
            agent_articles,
            profile,
            top_n=settings.MAX_ARTICLES_PER_FEED,
        )
    else:
        # Agent already ranked — just slice to limit
        ranked = agent_articles[:settings.MAX_ARTICLES_PER_FEED]
        print(f"🎯 Agent pre-ranked: using {len(ranked)} articles")

    if not ranked:
        cache_feed(user_id, [], ttl_seconds=60)
        return []

    print(f"🎯 LLM ranked: {len(ranked)} articles selected")

    # ── Step 5: AI Rewriter ───────────────────────────────────
    rewrite_tasks = [
        rewrite_article_for_user(article, profile)
        for article in ranked
    ]
    personalized = await asyncio.gather(*rewrite_tasks)
    print(f"✍️  Rewriter personalized {len(personalized)} articles")

    # ── Step 6: Build final feed + cache ──────────────────────
    feed = []
    for article in personalized:
        feed.append({
            "title":                article.get("title"),
            "url":                  article.get("url"),
            "source":               article.get("source"),
            "category":             article.get("category", ""),
            "tags":                 article.get("tags", []),
            "relevance_score":      article.get("relevance_score", 0),
            "matched_interest":     article.get("matched_interest", ""),
            "reason_for_selection": article.get("reason_for_selection", ""),
            "query_used":           article.get("query_used", ""),
            "personalized":         article.get("personalized", {}),
            "ai_generated":         article.get("ai_generated", False),
            "published":            str(article.get("published", "")),
            "agent_curated":        True,
        })

    cache_feed(user_id, feed, ttl_seconds=FEED_GRACE_TTL)
    print(f"✅ Feed cached for user {user_id} (grace TTL: {FEED_GRACE_TTL}s)\n")

    return feed


async def _run_agent(profile: dict) -> List[Dict]:
    """
    Run the PersonalizedIntelAgent to scrape Google News RSS
    based on the user's full interest list.

    The agent now includes an internal LLM ranking pass that returns
    articles pre-ranked with matched_interest assigned by AI reasoning.
    """
    from app.intel.personalized_agent import PersonalizedIntelAgent

    interests = profile.get("interests", [])
    if not interests:
        raise ValueError("User must complete profile setup with interests before a personalized feed can be generated.")

    agent = PersonalizedIntelAgent(profile)
    result = await agent.run()

    # Convert agent output into orchestrator format
    articles = []
    for art in result.get("articles", []):
        query = art.get("query_used", "")
        articles.append({
            "title":                art.get("title", ""),
            "summary":              art.get("summary", ""),
            "url":                  art.get("url", ""),
            "source":               art.get("source", "Google News"),
            "category":             _guess_category(query, interests),
            "tags":                 [query] if query else [],
            "relevance_score":      art.get("relevance_score", 1.0),
            "matched_interest":     art.get("matched_interest", ""),
            "reason_for_selection": art.get("reason_for_selection", ""),
            "query_used":           query,
            "published":            art.get("published", ""),
        })

    return articles


def _guess_category(query_used: str, interests: list) -> str:
    """Map the query used to a rough category for badge display."""
    q = query_used.lower()
    mapping = {
        "ai": "tech", "ml": "tech", "llm": "tech", "technology": "tech",
        "generative": "tech", "software": "tech",
        "startup": "startups", "funding": "startups", "venture": "startups",
        "unicorn": "startups", "founder": "startups",
        "stock": "markets", "equity": "markets", "sensex": "markets",
        "nifty": "markets", "ipo": "markets", "market": "markets",
        "bitcoin": "crypto", "crypto": "crypto", "blockchain": "crypto",
        "defi": "crypto", "web3": "crypto",
        "rbi": "finance", "economy": "finance", "gdp": "finance",
        "inflation": "finance", "bank": "finance", "budget": "finance",
        "health": "healthcare", "pharma": "healthcare", "biotech": "healthcare",
    }
    for keyword, cat in mapping.items():
        if keyword in q:
            return cat
    return "general"
