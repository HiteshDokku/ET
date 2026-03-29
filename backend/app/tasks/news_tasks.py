"""Celery tasks for news fetching.

Includes:
- fetch_and_cache_news: Periodic background task (every 15 min)
- priority_scrape: On-demand task for dashboard loads with timeout handling
"""

import json
import asyncio
import logging
import time

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks.news_tasks.fetch_and_cache_news",
)
def fetch_and_cache_news(self):
    """Periodic: Fetch latest news from RSS feeds and store in Redis.

    Uses httpx + feedparser (no Selenium) so it's lightweight
    and won't cause heartbeat issues.
    """
    import redis as redis_lib

    try:
        logger.info("🔄 Celery: Fetching fresh news from RSS feeds...")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from app.services.news_service import fetch_all_feeds
        articles = loop.run_until_complete(fetch_all_feeds())
        loop.close()

        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        r.setex("news:pool", 1800, json.dumps(articles, default=str))

        logger.info(f"✅ Celery: Cached {len(articles)} articles in Redis")
        return {"status": "success", "count": len(articles)}

    except Exception as exc:
        logger.error(f"❌ Celery fetch failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=1,
    name="app.tasks.news_tasks.priority_scrape",
    soft_time_limit=120,     # soft limit: 2 min
    time_limit=180,          # hard limit: 3 min
    acks_late=True,          # only ack after completion
)
def priority_scrape(self, user_id: int, profile: dict):
    """On-demand: Real-time scrape triggered by dashboard load.

    Runs the PersonalizedIntelAgent for the user's interests.
    Designed with tight timeouts so it doesn't block the Celery worker
    or cause heartbeat failures.

    Stores result directly in Redis under feed:{user_id}.

    Returns:
        dict with status ('completed' | 'partial' | 'failed'),
        article count, and elapsed time.
    """
    import redis as redis_lib
    from celery.exceptions import SoftTimeLimitExceeded

    r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    t0 = time.time()

    # Signal to frontend that scraping is in progress
    r.setex(
        f"feed_status:{user_id}",
        300,
        json.dumps({"status": "processing", "started_at": t0}),
    )

    try:
        logger.info(f"🧠 Priority scrape for user {user_id}: {profile.get('interests', [])}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        from app.intel.personalized_agent import PersonalizedIntelAgent
        agent = PersonalizedIntelAgent(profile)
        result = loop.run_until_complete(agent.run())
        loop.close()

        articles = result.get("articles", [])
        elapsed = round(time.time() - t0, 2)

        # Convert to feed format and cache
        feed_data = []
        for art in articles:
            feed_data.append({
                "title": art.get("title", ""),
                "url": art.get("url", ""),
                "source": art.get("source", "Google News"),
                "summary": art.get("summary", ""),
                "query_used": art.get("query_used", ""),
                "published": art.get("published", ""),
                "agent_curated": True,
            })

        r.setex(f"feed:{user_id}", 300, json.dumps(feed_data, default=str))
        r.setex(
            f"feed_status:{user_id}",
            300,
            json.dumps({"status": "completed", "count": len(articles), "elapsed": elapsed}),
        )

        logger.info(f"✅ Priority scrape done: {len(articles)} articles in {elapsed}s")
        return {"status": "completed", "count": len(articles), "elapsed": elapsed}

    except SoftTimeLimitExceeded:
        elapsed = round(time.time() - t0, 2)
        logger.warning(f"⏰ Priority scrape hit soft time limit ({elapsed}s)")

        # Return whatever partial results we have
        partial_count = len(getattr(self, '_saved_articles', []))
        r.setex(
            f"feed_status:{user_id}",
            300,
            json.dumps({"status": "partial", "count": partial_count, "elapsed": elapsed}),
        )
        return {"status": "partial", "count": partial_count, "elapsed": elapsed}

    except Exception as exc:
        elapsed = round(time.time() - t0, 2)
        logger.error(f"❌ Priority scrape failed after {elapsed}s: {exc}")

        r.setex(
            f"feed_status:{user_id}",
            300,
            json.dumps({"status": "failed", "error": str(exc), "elapsed": elapsed}),
        )
        return {"status": "failed", "error": str(exc), "elapsed": elapsed}
