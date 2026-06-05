from celery import Celery

from app.config import settings

celery_app = Celery(
    "badmframe",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_acks_late=True,
    worker_concurrency=1,
    task_track_started=True,
    result_expires=3600,
    imports=["app.tasks.export", "app.tasks.analysis"],
)
