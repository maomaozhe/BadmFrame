from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoMetadata:
    fps: float
    frame_width: int
    frame_height: int
    frame_count: int | None = None


def read_video_metadata(video_path: Path) -> VideoMetadata:
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    opencv_result = _read_with_opencv(video_path)
    if opencv_result is not None:
        return opencv_result

    ffprobe_result = _read_with_ffprobe(video_path)
    if ffprobe_result is not None:
        return ffprobe_result

    raise RuntimeError("Unable to read video metadata. Install opencv-python or ffprobe.")


def _read_with_opencv(video_path: Path) -> VideoMetadata | None:
    try:
        import cv2  # type: ignore
    except Exception:
        return None

    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            return None
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or width <= 0 or height <= 0:
            return None
        return VideoMetadata(fps=fps, frame_width=width, frame_height=height, frame_count=frame_count)
    finally:
        cap.release()


def _read_with_ffprobe(video_path: Path) -> VideoMetadata | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None

    cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,nb_frames",
        "-of",
        "json",
        str(video_path),
    ]
    completed = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        return None

    data = json.loads(completed.stdout)
    streams = data.get("streams") or []
    if not streams:
        return None
    stream = streams[0]
    fps = _parse_ratio(stream.get("r_frame_rate"))
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    frame_count_raw = stream.get("nb_frames")
    frame_count = int(frame_count_raw) if frame_count_raw and str(frame_count_raw).isdigit() else None
    if fps <= 0 or width <= 0 or height <= 0:
        return None
    return VideoMetadata(fps=fps, frame_width=width, frame_height=height, frame_count=frame_count)


def _parse_ratio(value: str | None) -> float:
    if not value:
        return 0
    if "/" not in value:
        return float(value)
    numerator, denominator = value.split("/", 1)
    denominator_value = float(denominator)
    if denominator_value == 0:
        return 0
    return float(numerator) / denominator_value

