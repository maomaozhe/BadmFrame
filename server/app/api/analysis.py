from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.clip import Clip
from app.models.project import Project
from app.models.video import SourceVideo
from app.schemas.analysis import (
    AnalysisParams,
    AnalysisResultRead,
    AnalysisStartResponse,
    AutoClipsApplyRequest,
    AutoClipsApplyResponse,
)
from app.services.analysis import create_analysis_task_id, load_analysis_result, run_video_analysis

router = APIRouter()


@router.post("/videos/{video_id}/analysis", response_model=AnalysisStartResponse, status_code=202)
async def start_video_analysis(
    video_id: str,
    body: AnalysisParams = AnalysisParams(),
    db: AsyncSession = Depends(get_db),
):
    video = await _get_video(video_id, db)
    task_id = create_analysis_task_id()

    # MVP runs synchronously so local development and tests do not require a
    # Redis/Celery worker. The pure task module uses the same service function.
    try:
        run_video_analysis(
            task_id=task_id,
            video_id=video.id,
            project_id=video.project_id,
            video_path=Path(video.file_path),
            duration_sec=video.duration_sec,
            body=body,
        )
    except FileNotFoundError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e
    return AnalysisStartResponse(task_id=task_id, status="completed")


@router.get("/videos/{video_id}/analysis/{task_id}", response_model=AnalysisResultRead)
async def get_video_analysis(video_id: str, task_id: str, db: AsyncSession = Depends(get_db)):
    await _get_video(video_id, db)
    result = load_analysis_result(task_id)
    if not result or result.video_id != video_id:
        raise HTTPException(404, "Analysis task not found")
    return result


@router.post("/projects/{project_id}/auto-clips/apply", response_model=AutoClipsApplyResponse)
async def apply_auto_clips(
    project_id: str,
    body: AutoClipsApplyRequest,
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project(project_id, db)
    result = load_analysis_result(body.task_id)
    if not result or result.project_id != project_id:
        raise HTTPException(404, "Analysis result not found for project")

    if body.replace_existing_auto:
        existing = await db.execute(
            select(Clip).where(Clip.project_id == project_id, Clip.notes.like("%source:auto-dead-time%"))
        )
        for clip in existing.scalars():
            await db.delete(clip)

    created_ids: list[str] = []
    keep_segments = [segment for segment in result.segments if segment.state == "keep"]
    for index, segment in enumerate(keep_segments, start=1):
        clip = Clip(
            start_time_sec=segment.start_sec,
            end_time_sec=segment.end_sec,
            label=f"自动回合 {index}",
            notes=f"source:auto-dead-time confidence:{segment.confidence:.2f} reason:{','.join(segment.reason)}",
            project_id=project.id,
        )
        db.add(clip)
        await db.flush()
        created_ids.append(clip.id)

    await db.commit()
    return AutoClipsApplyResponse(created_clip_ids=created_ids, clips_created=len(created_ids))


async def _get_video(video_id: str, db: AsyncSession) -> SourceVideo:
    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Video not found")
    return video


async def _get_project(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    return project
