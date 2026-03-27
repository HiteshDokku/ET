from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.agents.orchestrator import build_personalized_feed
from app.services.redis_service import redis_client, update_engagement

router = APIRouter(prefix="/news", tags=["News Feed"])


@router.get("/feed/{user_id}")
async def get_personalized_feed(user_id: int):
    """
    THE MAIN ENDPOINT.

    Returns a fully personalized news feed for a user.

    Flow:
    1. Check Redis for cached feed → return instantly if found (⚡ fast)
    2. If not cached → run full AI pipeline → cache → return

    A student gets simplified explainers.
    An investor gets market analysis.
    A founder gets startup ecosystem angles.
    """
    try:
        feed = await build_personalized_feed(user_id, redis_client)

        return {
            "user_id":       user_id,
            "article_count": len(feed),
            "articles":      feed,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feed generation failed: {str(e)}")


@router.post("/engage/{user_id}")
async def record_engagement(user_id: int, article_category: str, action: str = "read"):
    """
    Called when a user clicks / reads / skips an article.
    Updates their engagement profile in Redis.
    This makes the NEXT feed smarter.

    action: "read" | "click" | "skip"
    """
    if action in ("read", "click"):
        # Positive engagement → boost this category
        update_engagement(user_id, article_category, delta=0.1)
        message = f"Boosted interest in '{article_category}' for user {user_id}"
    elif action == "skip":
        # Negative engagement → reduce this category
        update_engagement(user_id, article_category, delta=-0.05)
        message = f"Reduced interest in '{article_category}' for user {user_id}"
    else:
        message = "Unknown action — no change"

    return {"status": "ok", "message": message}


@router.delete("/feed/{user_id}/cache")
async def invalidate_feed_cache(user_id: int):
    """
    Force-clears a user's cached feed.
    Useful when user updates their preferences and wants a fresh feed.
    """
    redis_client.delete(f"feed:{user_id}")
    return {"status": "ok", "message": f"Cache cleared for user {user_id}"}


@router.get("/pool/status")
async def news_pool_status():
    """
    Debug endpoint — shows how many articles are in the shared news pool.
    Useful for checking if Celery is working.
    """
    import json
    raw = redis_client.get("news:pool")
    if raw:
        articles = json.loads(raw)
        return {
            "status": "populated",
            "count": len(articles),
            "ttl_seconds": redis_client.ttl("news:pool"),
        }
    return {"status": "empty", "message": "Celery has not fetched news yet"}
