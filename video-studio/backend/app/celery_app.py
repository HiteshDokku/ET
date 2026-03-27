"""Celery application configuration."""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "video_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=900,  # 15 min hard limit
    task_soft_time_limit=600,  # 10 min soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=5,
)
