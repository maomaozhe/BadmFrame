from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.clip import Clip
from app.models.project import Project
from app.schemas.clip import ClipCreate, ClipRead, ClipUpdate

router = APIRouter()


@router.post("/{project_id}/clips", response_model=ClipRead, status_code=201)
async def create_clip(project_id: str, body: ClipCreate, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    clip = Clip(
        start_time_sec=body.start_time_sec,
        end_time_sec=body.end_time_sec,
        label=body.label,
        notes=body.notes,
        anchor_marker_id=body.anchor_marker_id,
        project_id=project_id,
    )
    db.add(clip)
    await db.commit()
    await db.refresh(clip)
    return clip


@router.put("/{project_id}/clips/{clip_id}", response_model=ClipRead)
async def update_clip(
    project_id: str, clip_id: str, body: ClipUpdate, db: AsyncSession = Depends(get_db)
):
    clip = await _get_clip(project_id, clip_id, db)
    for field in ("start_time_sec", "end_time_sec", "label", "notes", "anchor_marker_id",
                  "export_status", "exported_file_path"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(clip, field, val)
    await db.commit()
    await db.refresh(clip)
    return clip


@router.delete("/{project_id}/clips/{clip_id}", status_code=204)
async def delete_clip(project_id: str, clip_id: str, db: AsyncSession = Depends(get_db)):
    clip = await _get_clip(project_id, clip_id, db)
    # Remove exported file if exists
    if clip.exported_file_path:
        from pathlib import Path
        p = Path(clip.exported_file_path)
        if p.exists():
            p.unlink()
    await db.delete(clip)
    await db.commit()


async def _check_project(project_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Project not found")


async def _get_clip(project_id: str, clip_id: str, db: AsyncSession) -> Clip:
    result = await db.execute(
        select(Clip).where(Clip.id == clip_id, Clip.project_id == project_id)
    )
    clip = result.scalar_one_or_none()
    if not clip:
        raise HTTPException(404, "Clip not found")
    return clip
