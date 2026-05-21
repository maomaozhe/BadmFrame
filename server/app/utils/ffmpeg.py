import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    duration_sec: float = 0
    width: int = 0
    height: int = 0
    frame_rate: float = 0
    codec: str = ""
    is_vfr: bool = False


async def _run_ffprobe(file_path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")
    return json.loads(stdout)


async def extract_metadata(file_path: Path) -> VideoMetadata:
    data = await _run_ffprobe(file_path)
    meta = VideoMetadata()

    video_stream = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break

    if video_stream:
        meta.width = video_stream.get("width", 0)
        meta.height = video_stream.get("height", 0)
        meta.codec = video_stream.get("codec_name", "")
        fps_str = video_stream.get("r_frame_rate", "0/1")
        try:
            num, den = fps_str.split("/")
            meta.frame_rate = float(num) / float(den) if float(den) != 0 else 0
        except (ValueError, ZeroDivisionError):
            meta.frame_rate = 0
        # VFR detection: avg_frame_rate != r_frame_rate
        avg_fps_str = video_stream.get("avg_frame_rate", "0/1")
        meta.is_vfr = fps_str != avg_fps_str

    fmt = data.get("format", {})
    meta.duration_sec = float(fmt.get("duration", 0))
    return meta


async def generate_thumbnail(video_path: Path, time_sec: float, output_path: Path, size: str = "120x68") -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(time_sec),
        "-i", str(video_path),
        "-vframes", "1",
        "-s", size,
        "-q:v", "2",
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("Thumbnail generation failed at %.1fs: %s", time_sec, stderr.decode())
        return


async def run_export(video_path: Path, start_sec: float, end_sec: float, output_path: Path) -> None:
    """Export a clip using stream copy (fast, keyframe-precision)."""
    duration = end_sec - start_sec
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start_sec),
        "-i", str(video_path),
        "-t", str(duration),
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Export failed: {stderr.decode()}")
