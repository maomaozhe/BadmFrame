import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.clip import Clip
from app.utils.ffmpeg import run_concat_export, run_export

logger = logging.getLogger(__name__)


async def export_clip(clip: Clip, project_id: str, db: AsyncSession) -> None:
    if not clip.project.source_video:
        raise ValueError("Project has no source video")

    video_path = Path(clip.project.source_video.file_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Source video not found: {video_path}")

    out_dir = settings.exports_dir / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{clip.id}.mp4"

    clip.export_status = "exporting"
    await db.commit()

    await run_export(video_path, clip.start_time_sec, clip.end_time_sec, out_path)

    clip.export_status = "completed"
    clip.exported_file_path = str(out_path)
    await db.commit()


async def cancel_export(clip: Clip, db: AsyncSession) -> None:
    if clip.exported_file_path:
        path = Path(clip.exported_file_path)
        if path.exists():
            path.unlink()
    clip.export_status = "failed"
    clip.exported_file_path = None
    await db.commit()


async def export_clip_sequence(clips: list[Clip], project_id: str, preset: str = "auto") -> Path:
    if not clips:
        raise ValueError("No clips selected")
    project = clips[0].project
    if not project.source_video:
        raise ValueError("Project has no source video")

    video_path = Path(project.source_video.file_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Source video not found: {video_path}")

    sorted_clips = sorted(clips, key=lambda clip: clip.start_time_sec)
    ranges = [(clip.start_time_sec, clip.end_time_sec) for clip in sorted_clips]
    out_dir = settings.exports_dir / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "auto_dead_time_edit.mp4"
    await run_concat_export(video_path, ranges, out_path, preset=preset)
    return out_path
