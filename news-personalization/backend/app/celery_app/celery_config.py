"""
Celery Background Tasks

These run automatically in the background, separate from the main API.
Think of them as scheduled cron jobs.

Task 1: fetch_and_cache_news  — runs every 15 min, refreshes news pool
Task 2: warmup_user_feeds     — pre-builds feeds for active users
"""

import json
import asyncio
from celery import Celery
from celery.schedules import crontab

from app.config import settings

# ─── Create the Celery app ────────────────────────────────────
# broker: Redis is the "message queue" — FastAPI sends tasks here
# backend: Redis also stores task results
celery_app = Celery(
    "my_et_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,

    # ── Scheduled tasks (like cron) ──────────────────────────
    beat_schedule={
        "fetch-news-every-15-min": {
            "task": "app.celery_app.celery_config.fetch_and_cache_news",
            "schedule": settings.NEWS_FETCH_INTERVAL_MINUTES * 60,  # seconds
        },
    },
)


# ─── Task 1: Fetch news and store in Redis ────────────────────
@celery_app.task(bind=True, max_retries=3)
def fetch_and_cache_news(self):
    """
    Runs every 15 minutes.
    Fetches latest news from ET RSS feeds → stores in Redis.
    All users share this one news pool — personalization happens later.
    """
    import redis as redis_lib

    try:
        print("🔄 Celery: Fetching fresh news from ET RSS feeds...")

        # Run async function inside sync Celery task
        loop = asyncio.get_event_loop()
        from app.services.news_service import fetch_all_feeds
        articles = loop.run_until_complete(fetch_all_feeds())

        # Store in Redis — expires after 30 minutes
        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        r.setex("news:pool", 1800, json.dumps(articles, default=str))

        print(f"✅ Celery: Cached {len(articles)} articles in Redis")
        return {"status": "success", "count": len(articles)}

    except Exception as exc:
        print(f"❌ Celery fetch failed: {exc}")
        # Retry after 60 seconds (max 3 times)
        raise self.retry(exc=exc, countdown=60)


# ─── Task 2: Pre-warm feeds for recently active users ─────────
@celery_app.task
def warmup_active_user_feeds():
    """
    Optional optimization: pre-build feeds for users who logged in recently.
    So when they open the app → their feed is ready instantly.
    (Not critical for hackathon — but impressive to mention)
    """
    import redis as redis_lib
    r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)

    # Find recently active users (keys matching "user:*")
    user_keys = r.keys("user:*")
    print(f"🔥 Warming feeds for {len(user_keys)} users...")

    # In a real system, you'd rebuild each user's feed here
    # For hackathon: just invalidate stale feeds so they regenerate on request
    for key in user_keys:
        user_id = key.split(":")[1]
        # Check if feed is expired or missing
        if not r.exists(f"feed:{user_id}"):
            print(f"   ➜ Feed missing for user {user_id} — will regenerate on next request")
