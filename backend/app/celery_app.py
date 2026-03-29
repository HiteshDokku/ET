"""Unified Celery application configuration.

Heartbeat and resource settings tuned to prevent timeouts caused by
Selenium-heavy scraping tasks blocking the worker event loop.
"""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "et_combined",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.video_tasks",
        "app.tasks.news_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=900,
    task_soft_time_limit=600,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=5,

    # ── Heartbeat — prevent false-positive disconnects ────────
    # Increase broker heartbeat to tolerate slow scraping tasks.
    # Default is 120s; we set 10s interval but allow 60s grace.
    broker_heartbeat=10,
    broker_heartbeat_checkrate=6,       # check every 6 * 10 = 60s
    broker_transport_options={
        "visibility_timeout": 3600,     # task can run up to 1 hour
    },

    # ── Worker health ─────────────────────────────────────────
    worker_lost_wait=30,                # wait 30s before declaring lost
    worker_cancel_long_running_tasks_on_connection_loss=True,

    # Route tasks to specific queues
    task_routes={
        "app.tasks.video_tasks.*": {"queue": "video"},
        "app.tasks.news_tasks.*": {"queue": "news"},
    },

    # Scheduled tasks
    beat_schedule={
        "fetch-news-every-15-min": {
            "task": "app.tasks.news_tasks.fetch_and_cache_news",
            "schedule": settings.NEWS_FETCH_INTERVAL_MINUTES * 60,
            "options": {"queue": "news"},
        },
    },
)
