from __future__ import annotations

from pathlib import Path

from app.services.rally_detection import run_rally_detection
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.detect_rallies")
def detect_rallies(
    self,
    *,
    task_id: str,
    video_id: str,
    project_id: str | None,
    video_path: str,
) -> dict:
    """Celery task that runs the full TrackNetV3 rally-detection pipeline."""
    result = run_rally_detection(
        task_id=task_id,
        video_id=video_id,
        project_id=project_id,
        video_path=Path(video_path),
    )
    return result
