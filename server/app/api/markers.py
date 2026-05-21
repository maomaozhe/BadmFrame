from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.marker import Marker
from app.models.project import Project
from app.schemas.marker import MarkerCreate, MarkerRead, MarkerUpdate

router = APIRouter()


@router.post("/{project_id}/markers", response_model=MarkerRead, status_code=201)
async def create_marker(project_id: str, body: MarkerCreate, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    marker = Marker(
        timestamp_sec=body.timestamp_sec,
        label=body.label,
        color=body.color,
        project_id=project_id,
    )
    db.add(marker)
    await db.commit()
    await db.refresh(marker)
    return marker


@router.put("/{project_id}/markers/{marker_id}", response_model=MarkerRead)
async def update_marker(
    project_id: str, marker_id: str, body: MarkerUpdate, db: AsyncSession = Depends(get_db)
):
    marker = await _get_marker(project_id, marker_id, db)
    if body.timestamp_sec is not None:
        marker.timestamp_sec = body.timestamp_sec
    if body.label is not None:
        marker.label = body.label
    if body.color is not None:
        marker.color = body.color
    await db.commit()
    await db.refresh(marker)
    return marker


@router.delete("/{project_id}/markers/{marker_id}", status_code=204)
async def delete_marker(project_id: str, marker_id: str, db: AsyncSession = Depends(get_db)):
    marker = await _get_marker(project_id, marker_id, db)
    await db.delete(marker)
    await db.commit()


async def _check_project(project_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Project not found")


async def _get_marker(project_id: str, marker_id: str, db: AsyncSession) -> Marker:
    result = await db.execute(
        select(Marker).where(Marker.id == marker_id, Marker.project_id == project_id)
    )
    marker = result.scalar_one_or_none()
    if not marker:
        raise HTTPException(404, "Marker not found")
    return marker
