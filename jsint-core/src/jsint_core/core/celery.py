from celery import Celery

from .config import settings

celery = Celery(
    "jsint",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "jsint_core.tasks.event",
        "jsint_core.tasks.enricher",
        "jsint_core.tasks.flow",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=4,  # Allow each worker to prefetch up to 4 tasks
)
