"""Celery application factory."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "saas",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "renew-subscriptions-hourly": {
            "task": "app.tasks.jobs.renew_subscriptions",
            "schedule": 3600.0,
        },
    },
)
