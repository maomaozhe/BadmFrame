import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.video import SourceVideo
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.storage import cleanup_project_files

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(name=body.name)
    db.add(project)

    if body.video_id:
        result = await db.execute(select(SourceVideo).where(SourceVideo.id == body.video_id))
        video = result.scalar_one_or_none()
        if not video:
            raise HTTPException(404, "Video not found")
        if video.project_id is not None:
            raise HTTPException(400, "Video already assigned to another project")
        video.project = project

    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).order_by(Project.updated_at.desc())
    )
    return list(result.scalars().unique())


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await _get_project(project_id, db)
    return project


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: str, body: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    project = await _get_project(project_id, db)
    if body.name is not None:
        project.name = body.name
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await _get_project(project_id, db)
    cleanup_project_files(project_id)
    await db.delete(project)
    await db.commit()


async def _get_project(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    return project
