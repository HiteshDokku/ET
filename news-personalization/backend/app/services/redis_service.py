import redis
import json
from app.config import settings

# Create one Redis client — reused everywhere
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_user_profile(user_id: int) -> dict | None:
    """
    Fetch user profile from Redis (fast).
    Returns None if not cached (then fetch from DB instead).
    """
    raw = redis_client.get(f"user:{user_id}")
    if raw:
        try:
            # Try to parse as JSON first
            import json
            return json.loads(raw)
        except:
            # Fallback to literal_eval for old format
            import ast
            try:
                return ast.literal_eval(raw)
            except:
                print(f"❌ Failed to parse user profile for {user_id}")
                return None
    return None


def get_cached_feed(user_id: int) -> list | None:
    """
    Get a pre-built feed from Redis.
    Returns None if cache is empty / expired.
    """
    raw = redis_client.get(f"feed:{user_id}")
    if raw:
        return json.loads(raw)
    return None


def cache_feed(user_id: int, feed: list, ttl_seconds: int = 900):
    """
    Save a user's personalized feed in Redis.
    Default TTL = 15 minutes (900 seconds).
    After 15 min, the feed expires and gets regenerated on next request.
    """
    redis_client.setex(
        f"feed:{user_id}",
        ttl_seconds,
        json.dumps(feed, default=str)   # default=str handles datetime objects
    )


def update_engagement(user_id: int, category: str, delta: float = 0.1):
    """
    Bump up the engagement score for a category when a user clicks/reads.
    This is how the system learns user preferences over time.

    Example: user reads an AI article → AI score goes from 0.5 → 0.6
    """
    import json
    raw = redis_client.get(f"user:{user_id}")
    if not raw:
        return

    try:
        profile = json.loads(raw)
    except:
        import ast
        profile = ast.literal_eval(raw)

    engagement = profile.get("engagement", {})

    # Increase score for clicked category (max 1.0)
    current = engagement.get(category, 0.5)
    engagement[category] = min(1.0, current + delta)

    profile["engagement"] = engagement
    redis_client.setex(f"user:{user_id}", 86400, json.dumps(profile))

    # Also invalidate the old cached feed so next one uses updated preferences
    redis_client.delete(f"feed:{user_id}")
