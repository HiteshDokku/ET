"""News feed routes — real-time agentic personalized news endpoints.

Includes force_refresh support and Article DB fallback to prevent
empty feeds when the agent or cache is unavailable.
"""

import json
import time
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.agents.orchestrator import build_personalized_feed
from app.services.redis_service import redis_client, update_engagement
from app.clerk_auth import get_clerk_user_id
from app.routes.auth import get_or_create_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["News Feed"])


@router.get("/feed")
async def get_personalized_feed(
    force_refresh: bool = Query(False, description="Bypass cache and trigger fresh agent scrape"),
    clerk_id: str = Depends(get_clerk_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Real-time personalized news feed for the Dashboard.

    Pipeline:
    1. If force_refresh=true, delete cached feed first
    2. Check Redis feed:{user_id} for 5-min grace cache → return if fresh
    3. Run PersonalizedIntelAgent → scrape Google News RSS for ALL interests
    4. Diversity-first TF-IDF ranking → 15 articles covering every interest
    5. AI rewriter → role-appropriate personalization
    6. Cache result (5 min grace) → return to Dashboard

    If the agent fails or times out, falls back to stored articles
    from the Article DB model to prevent showing an empty feed.
    """
    try:
        t0 = time.time()
        user = await get_or_create_user(clerk_id, db)

        # ── Force refresh: nuke the cache ─────────────────────
        if force_refresh:
            redis_client.delete(f"feed:{user.id}")
            logger.info(f"🔄 Force refresh for user {user.id} — cache cleared")

        # ── Try the agent pipeline ────────────────────────────
        try:
            feed = await build_personalized_feed(user.id, redis_client)
        except Exception as agent_err:
            logger.error(f"⚠️ Agent pipeline failed: {agent_err}")
            feed = []

        # ── Fallback: Article DB if agent returned nothing ────
        if not feed:
            logger.info(f"📦 Agent empty — falling back to Article DB for user {user.id}")
            feed = await _db_fallback(db, user)

        elapsed = round(time.time() - t0, 2)

        # ── Response metadata ─────────────────────────────────
        agent_curated = any(a.get("agent_curated", False) for a in feed) if feed else False
        matched_interests = list({
            a.get("matched_interest", "")
            for a in feed
            if a.get("matched_interest")
        })

        interest_counts = {}
        for a in feed:
            mi = a.get("matched_interest", "")
            if mi:
                interest_counts[mi] = interest_counts.get(mi, 0) + 1

        return {
            "user_id": user.id,
            "article_count": len(feed),
            "agent_curated": agent_curated,
            "matched_interests": matched_interests,
            "interest_distribution": interest_counts,
            "elapsed_seconds": elapsed,
            "force_refreshed": force_refresh,
            "articles": feed,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feed generation failed: {str(e)}")


async def _db_fallback(db: AsyncSession, user) -> list[dict]:
    """Load recent articles from the Article DB as a fallback.

    Used when the agent pipeline fails or returns empty results,
    so the user never sees a completely blank dashboard.
    """
    try:
        from app.models.user import Article

        result = await db.execute(
            select(Article)
            .order_by(desc(Article.fetched_at))
            .limit(15)
        )
        rows = result.scalars().all()

        feed = []
        for row in rows:
            feed.append({
                "title": row.title,
                "url": row.url,
                "source": row.source or "ET",
                "category": row.category or "general",
                "tags": [],
                "relevance_score": 0.5,
                "matched_interest": "",
                "query_used": "",
                "personalized": {},
                "ai_generated": False,
                "published": str(row.published or row.fetched_at or ""),
                "agent_curated": False,
            })

        logger.info(f"📦 DB fallback returned {len(feed)} articles")
        return feed

    except Exception as e:
        logger.error(f"❌ DB fallback failed: {e}")
        return []


@router.get("/feed/status")
async def get_feed_status(
    clerk_id: str = Depends(get_clerk_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Check the status of an ongoing priority scrape.

    Frontend can poll this endpoint to show real-time progress
    when the agent is running.

    Returns: {status: 'processing'|'completed'|'partial'|'failed', ...}
    """
    user = await get_or_create_user(clerk_id, db)
    raw = redis_client.get(f"feed_status:{user.id}")
    if raw:
        return json.loads(raw)
    return {"status": "idle", "message": "No active scrape"}


@router.post("/engage")
async def record_engagement(
    article_category: str,
    action: str = "read",
    clerk_id: str = Depends(get_clerk_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Record user engagement with an article."""
    user = await get_or_create_user(clerk_id, db)

    if action in ("read", "click"):
        update_engagement(user.id, article_category, delta=0.1)
        message = f"Boosted interest in '{article_category}'"
    elif action == "skip":
        update_engagement(user.id, article_category, delta=-0.05)
        message = f"Reduced interest in '{article_category}'"
    else:
        message = "Unknown action — no change"

    return {"status": "ok", "message": message}


@router.delete("/feed/cache")
async def invalidate_feed_cache(
    clerk_id: str = Depends(get_clerk_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Clear cached feed to force a fresh agent scrape on next load."""
    user = await get_or_create_user(clerk_id, db)
    redis_client.delete(f"feed:{user.id}")
    redis_client.delete(f"feed_status:{user.id}")
    return {"status": "ok", "message": "Cache cleared — next load will trigger fresh agent scrape"}


@router.get("/pool/status")
async def news_pool_status():
    """Debug endpoint — shows feed cache status."""
    raw = redis_client.get("news:pool")
    if raw:
        articles = json.loads(raw)
        return {
            "status": "populated",
            "count": len(articles),
            "ttl_seconds": redis_client.ttl("news:pool"),
        }
    return {"status": "empty", "message": "No global pool — agent scrapes on demand"}
