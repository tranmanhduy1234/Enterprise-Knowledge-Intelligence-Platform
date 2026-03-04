"""Celery application for async workers."""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ekip_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.ingest"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    result_expires=3600
)