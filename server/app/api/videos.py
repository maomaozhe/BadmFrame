import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.video import SourceVideo
from app.schemas.video import SourceVideoRead
from app.services.storage import save_upload
from app.services.video import create_source_video

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=SourceVideoRead, status_code=201)
async def upload_video(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(400, "File must be a video")
    try:
        dest, content_sha256 = await save_upload(file)
    except Exception as e:
        raise HTTPException(500, f"Failed to save upload: {e}")

    file_size = dest.stat().st_size
    try:
        video = await create_source_video(dest, dest.name, file_size, content_sha256)
    except Exception as e:
        dest.unlink(missing_ok=True)
        logger.error("Failed to extract video metadata: %s", e)
        raise HTTPException(400, f"Unplayable video: {e}")

    project = Project(name=dest.name.rsplit(".", 1)[0])
    db.add(project)
    await db.flush()
    video.project_id = project.id
    db.add(video)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        dest.unlink(missing_ok=True)
        # Find existing video with same content hash
        result = await db.execute(
            select(SourceVideo).where(SourceVideo.content_sha256 == content_sha256)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return JSONResponse(
                status_code=200,
                content={
                    "detail": "This video has already been uploaded.",
                    "video_id": existing.id,
                    "project_id": existing.project_id,
                    "file_name": existing.file_name,
                },
            )
        raise HTTPException(500, "Duplicate video detected but existing record not found")

    await db.refresh(video)
    return video


@router.get("/{video_id}", response_model=SourceVideoRead)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Video not found")
    return video


@router.get("/{video_id}/file")
async def stream_video_file(video_id: str, db: AsyncSession = Depends(get_db)):
    """Stream the source video file for browser playback / export."""
    from sqlalchemy import select

    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Video not found")
    file_path = Path(video.file_path)
    if not file_path.exists():
        raise HTTPException(404, "Video file not found on disk")
    return FileResponse(file_path, media_type="video/mp4")
