from pathlib import Path

from app.config import settings
from app.utils.ffmpeg import generate_thumbnail as _ffmpeg_thumbnail


async def generate_thumbnail(video_path: Path, time_sec: float, project_id: str) -> Path | None:
    out_dir = settings.thumbnails_dir / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"thumb_{int(time_sec)}.jpg"
    await _ffmpeg_thumbnail(video_path, time_sec, out_path)
    return out_path if out_path.exists() else None
