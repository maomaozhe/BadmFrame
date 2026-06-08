from pathlib import Path

from app.models.video import SourceVideo
from app.utils.ffmpeg import extract_metadata


async def create_source_video(
    file_path: Path,
    file_name: str,
    file_size: int,
    content_sha256: str | None = None,
) -> SourceVideo:
    meta = await extract_metadata(file_path)
    return SourceVideo(
        file_name=file_name,
        file_path=str(file_path),
        duration_sec=meta.duration_sec,
        width=meta.width,
        height=meta.height,
        frame_rate=meta.frame_rate,
        codec=meta.codec,
        is_vfr=meta.is_vfr,
        file_size=file_size,
        content_sha256=content_sha256,
    )
