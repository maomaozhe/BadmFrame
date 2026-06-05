from pathlib import Path

from celery import shared_task

from app.schemas.analysis import AnalysisParams
from app.services.analysis import run_video_analysis


@shared_task(bind=True)
def analyze_video(
    self,
    *,
    task_id: str,
    video_id: str,
    project_id: str | None,
    video_path: str,
    duration_sec: float,
    params: dict,
) -> dict:
    result = run_video_analysis(
        task_id=task_id,
        video_id=video_id,
        project_id=project_id,
        video_path=Path(video_path),
        duration_sec=duration_sec,
        body=AnalysisParams.model_validate(params),
    )
    return result.model_dump()
