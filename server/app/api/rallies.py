from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.clip import Clip
from app.models.project import Project
from app.models.rally_job import RallyJob
from app.models.video import SourceVideo
from app.schemas.rally import (
    RallyAnalysisResultRead,
    RallyCandidateRead,
    RallyCandidatesApplyRequest,
    RallyCandidatesApplyResponse,
)
from app.services.rally_import import parse_rally_candidates_payload

router = APIRouter()


@router.post("/videos/{video_id}/rallies/import", response_model=RallyAnalysisResultRead)
async def import_video_rallies(
    video_id: str,
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    video = await _get_video(video_id, db)
    try:
        candidates = parse_rally_candidates_payload(body)
    except (ValueError, ValidationError) as e:
        raise HTTPException(422, str(e)) from e

    result = RallyAnalysisResultRead(
        task_id=str(uuid.uuid4()),
        video_id=video.id,
        project_id=video.project_id,
        status="completed",
        progress=1,
        duration_sec=video.duration_sec,
        candidates=candidates,
        error=None,
    )
    save_rally_result(result)
    return result


@router.get("/videos/{video_id}/rallies/{task_id}", response_model=RallyAnalysisResultRead)
async def get_video_rallies(video_id: str, task_id: str, db: AsyncSession = Depends(get_db)):
    await _get_video(video_id, db)
    result = load_rally_result(task_id)
    if not result or result.video_id != video_id:
        raise HTTPException(404, "Rally task not found")
    return result


@router.post("/projects/{project_id}/rallies/apply", response_model=RallyCandidatesApplyResponse)
async def apply_rally_candidates(
    project_id: str,
    body: RallyCandidatesApplyRequest,
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project(project_id, db)
    result = load_rally_result(body.task_id)
    if not result or result.project_id != project_id:
        raise HTTPException(404, "Rally result not found for project")

    candidates = _apply_candidate_updates(result.candidates, body)
    if body.replace_existing_rally:
        existing = await db.execute(
            select(Clip).where(Clip.project_id == project_id, Clip.notes.like("%source:rally-candidate%"))
        )
        for clip in existing.scalars():
            await db.delete(clip)

    clip_candidates = [
        candidate
        for candidate in candidates
        if candidate.review_state in {"accepted", "adjusted"} or (body.include_pending and candidate.review_state == "pending")
    ]

    created_ids: list[str] = []
    for index, candidate in enumerate(sorted(clip_candidates, key=lambda item: item.start_sec), start=1):
        clip = Clip(
            start_time_sec=candidate.start_sec,
            end_time_sec=candidate.end_sec,
            label=f"有效回合 {index}",
            notes=(
                "source:rally-candidate "
                f"candidate:{candidate.id} confidence:{candidate.confidence:.2f} "
                f"state:{candidate.review_state}"
            ),
            project_id=project.id,
        )
        db.add(clip)
        await db.flush()
        created_ids.append(clip.id)

    await db.commit()
    return RallyCandidatesApplyResponse(created_clip_ids=created_ids, clips_created=len(created_ids))


def save_rally_result(result: RallyAnalysisResultRead) -> None:
    _rallies_dir().mkdir(parents=True, exist_ok=True)
    path = _rallies_dir() / f"{result.task_id}.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def load_rally_result(task_id: str) -> RallyAnalysisResultRead | None:
    path = _rallies_dir() / f"{task_id}.json"
    if not path.exists():
        return None
    return RallyAnalysisResultRead.model_validate(json.loads(path.read_text(encoding="utf-8")))


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


def _apply_candidate_updates(
    candidates: list[RallyCandidateRead],
    body: RallyCandidatesApplyRequest,
) -> list[RallyCandidateRead]:
    if not body.candidates:
        return candidates

    updates_by_id = {update.id: update for update in body.candidates}
    updated: list[RallyCandidateRead] = []
    for candidate in candidates:
        update = updates_by_id.get(candidate.id)
        if not update:
            updated.append(candidate)
            continue
        data = candidate.model_dump()
        for field in ("start_sec", "end_sec", "review_state"):
            value = getattr(update, field)
            if value is not None:
                data[field] = value
        updated.append(RallyCandidateRead.model_validate(data))
    return updated


def _rallies_dir():
    return settings.storage_dir / "rallies"
