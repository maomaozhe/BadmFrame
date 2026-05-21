import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
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
        dest = await save_upload(file)
    except Exception as e:
        raise HTTPException(500, f"Failed to save upload: {e}")

    file_size = dest.stat().st_size
    try:
        video = await create_source_video(dest, dest.name, file_size)
    except Exception as e:
        dest.unlink(missing_ok=True)
        logger.error("Failed to extract video metadata: %s", e)
        raise HTTPException(400, f"Unplayable video: {e}")

    db.add(video)
    await db.commit()
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
