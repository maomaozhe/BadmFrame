import asyncio
import json
import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

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
    ffprobe = _resolve_binary(settings.ffprobe_path)
    cmd = [
        ffprobe,
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
    ffmpeg = _resolve_binary(settings.ffmpeg_path)
    cmd = [
        ffmpeg,
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
    ffmpeg = _resolve_binary(settings.ffmpeg_path)
    duration = end_sec - start_sec
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
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


async def run_concat_export(
    video_path: Path,
    ranges: list[tuple[float, float]],
    output_path: Path,
) -> None:
    """Export multiple source ranges and concatenate them into one MP4.

    This favors compatibility over speed by encoding normalized intermediate
    MP4 files before concat. It is the server-side path for “remove dead time”
    exports where many keep segments become one continuous recap.
    """
    if not ranges:
        raise ValueError("No ranges to export")

    ffmpeg = _resolve_binary(settings.ffmpeg_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="badmframe_concat_") as tmp:
        tmp_dir = Path(tmp)
        part_paths: list[Path] = []
        for index, (start_sec, end_sec) in enumerate(ranges):
            duration = end_sec - start_sec
            if duration <= 0:
                continue
            part_path = tmp_dir / f"part_{index:04d}.mp4"
            part_paths.append(part_path)
            cmd = [
                ffmpeg,
                "-y",
                "-ss",
                str(start_sec),
                "-i",
                str(video_path),
                "-t",
                str(duration),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(part_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"Concat part export failed: {stderr.decode()}")

        if not part_paths:
            raise ValueError("No valid ranges to export")

        list_path = tmp_dir / "concat.txt"
        list_path.write_text(
            "\n".join(f"file '{path.as_posix()}'" for path in part_paths),
            encoding="utf-8",
        )
        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"Concat export failed: {stderr.decode()}")


def _resolve_binary(configured: str) -> str:
    path = Path(configured)
    if path.is_absolute() or "/" in configured:
        return str(path)
    return shutil.which(configured) or configured
