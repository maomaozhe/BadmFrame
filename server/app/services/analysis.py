from __future__ import annotations

import json
import math
import shutil
import subprocess
import uuid
from array import array
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

from app.config import settings
from app.schemas.analysis import AnalysisParams, AnalysisResultRead, AnalysisSegment


@dataclass(frozen=True)
class FeatureWindow:
    start_sec: float
    end_sec: float
    motion_score: float
    audio_score: float = 0

    @property
    def play_score(self) -> float:
        return self.motion_score * 0.7 + self.audio_score * 0.3


@dataclass(frozen=True)
class DetectionParams:
    mode: str
    enter_quantile: float
    low_quantile: float
    min_activity_sec: float
    idle_exit_sec: float
    pre_buffer_sec: float
    post_buffer_sec: float
    merge_gap_sec: float
    min_keep_sec: float


MODE_PARAMS: dict[str, DetectionParams] = {
    "conservative": DetectionParams("conservative", 0.52, 0.30, 1.5, 5.0, 3.0, 4.0, 3.0, 3.0),
    "balanced": DetectionParams("balanced", 0.60, 0.35, 2.0, 4.0, 2.0, 3.0, 2.0, 4.0),
    "aggressive": DetectionParams("aggressive", 0.68, 0.42, 2.5, 3.0, 1.0, 2.0, 1.5, 5.0),
}


def params_for_mode(body: AnalysisParams) -> DetectionParams:
    params = MODE_PARAMS[body.mode]
    return DetectionParams(
        mode=params.mode,
        enter_quantile=params.enter_quantile,
        low_quantile=params.low_quantile,
        min_activity_sec=params.min_activity_sec,
        idle_exit_sec=params.idle_exit_sec,
        pre_buffer_sec=body.pre_buffer_sec if body.pre_buffer_sec is not None else params.pre_buffer_sec,
        post_buffer_sec=body.post_buffer_sec if body.post_buffer_sec is not None else params.post_buffer_sec,
        merge_gap_sec=params.merge_gap_sec,
        min_keep_sec=params.min_keep_sec,
    )


def detect_play_windows(
    features: list[FeatureWindow],
    params: DetectionParams,
    duration_sec: float | None = None,
) -> list[AnalysisSegment]:
    """Detect keep/cut segments with a small activity state machine."""
    if not features:
        return []

    duration = duration_sec or features[-1].end_sec
    scores = [f.play_score for f in features]
    high_threshold = _quantile(scores, params.enter_quantile)
    low_threshold = _quantile(scores, params.low_quantile)
    if math.isclose(high_threshold, low_threshold):
        high_threshold = low_threshold + 0.001

    state = "idle"
    candidate_start: float | None = None
    play_start: float | None = None
    low_start: float | None = None
    keep_ranges: list[tuple[float, float, list[str], float]] = []

    for window in features:
        score = window.play_score
        high = score >= high_threshold
        low = score <= low_threshold

        if state == "idle":
            if high:
                state = "candidate_play"
                candidate_start = window.start_sec
        elif state == "candidate_play":
            if high and candidate_start is not None:
                if window.end_sec - candidate_start >= params.min_activity_sec:
                    state = "playing"
                    play_start = candidate_start
            elif low:
                state = "idle"
                candidate_start = None
        elif state == "playing":
            if low:
                state = "candidate_idle"
                low_start = window.start_sec
        elif state == "candidate_idle":
            if high:
                state = "playing"
                low_start = None
            elif low and low_start is not None and window.end_sec - low_start >= params.idle_exit_sec:
                if play_start is not None:
                    keep_ranges.append((play_start, low_start, ["high_motion", "sustained_activity"], _confidence(features, play_start, low_start, high_threshold)))
                state = "idle"
                candidate_start = None
                play_start = None
                low_start = None

    if state in {"playing", "candidate_idle"} and play_start is not None:
        end = low_start if low_start is not None else duration
        keep_ranges.append((play_start, end, ["high_motion", "video_tail"], _confidence(features, play_start, end, high_threshold)))

    buffered = [
        (
            max(0, start - params.pre_buffer_sec),
            min(duration, end + params.post_buffer_sec),
            reason,
            confidence,
        )
        for start, end, reason, confidence in keep_ranges
        if end > start
    ]
    merged = _merge_keep_ranges(buffered, params.merge_gap_sec)
    keep_segments = [
        AnalysisSegment(
            start_sec=round(start, 3),
            end_sec=round(end, 3),
            confidence=round(confidence, 2),
            reason=reason,
            state="keep",
        )
        for start, end, reason, confidence in merged
        if end - start >= params.min_keep_sec
    ]
    return _with_cut_segments(keep_segments, duration)


def extract_motion_features(video_path: Path, duration_sec: float, window_sec: float = 1.0) -> list[FeatureWindow]:
    """Extract real video/audio activity features from a source video."""
    if duration_sec <= 0:
        return []
    if not video_path.exists():
        raise FileNotFoundError(f"Source video not found: {video_path}")
    if not _has_ffmpeg():
        raise RuntimeError("FFmpeg is required for video analysis. Set BADMFRAME_FFMPEG_PATH or install ffmpeg.")

    real_features = _extract_ffmpeg_features(video_path, duration_sec, window_sec)
    if not real_features:
        raise RuntimeError("FFmpeg analysis produced no feature windows")
    return real_features


def _extract_ffmpeg_features(video_path: Path, duration_sec: float, window_sec: float) -> list[FeatureWindow]:
    motion_scores = _extract_frame_motion_scores(video_path, duration_sec, window_sec)
    if not motion_scores:
        return []
    try:
        audio_scores = _extract_audio_scores(video_path, duration_sec, window_sec)
    except Exception:
        audio_scores = []

    total = max(1, math.ceil(duration_sec / window_sec))
    windows: list[FeatureWindow] = []
    for index in range(total):
        start = index * window_sec
        end = min(duration_sec, start + window_sec)
        windows.append(
            FeatureWindow(
                start_sec=start,
                end_sec=end,
                motion_score=motion_scores[index] if index < len(motion_scores) else 0,
                audio_score=audio_scores[index] if index < len(audio_scores) else 0,
            )
        )
    return windows


def _extract_frame_motion_scores(
    video_path: Path,
    duration_sec: float,
    window_sec: float,
    fps: int = 3,
    width: int = 96,
    height: int = 54,
) -> list[float]:
    ffmpeg = _resolve_ffmpeg()
    if not ffmpeg:
        return []

    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(video_path),
        "-an",
        "-vf",
        f"fps={fps},scale={width}:{height},format=gray",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        timeout=_analysis_timeout(duration_sec),
    )

    frame_size = width * height
    raw = proc.stdout
    total_windows = max(1, math.ceil(duration_sec / window_sec))
    sums = [0.0] * total_windows
    counts = [0] * total_windows
    prev: bytes | None = None

    frame_count = len(raw) // frame_size
    for frame_index in range(frame_count):
        frame = raw[frame_index * frame_size : (frame_index + 1) * frame_size]
        if prev is not None:
            diff = sum(abs(a - b) for a, b in zip(frame, prev)) / (frame_size * 255)
            t = frame_index / fps
            bucket = min(total_windows - 1, max(0, int(t // window_sec)))
            sums[bucket] += diff
            counts[bucket] += 1
        prev = frame

    return _normalize_scores([
        sums[i] / counts[i] if counts[i] else 0
        for i in range(total_windows)
    ])


def _extract_audio_scores(
    video_path: Path,
    duration_sec: float,
    window_sec: float,
    sample_rate: int = 8000,
) -> list[float]:
    ffmpeg = _resolve_ffmpeg()
    if not ffmpeg:
        return []

    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "s16le",
        "pipe:1",
    ]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        timeout=_analysis_timeout(duration_sec),
    )

    total_windows = max(1, math.ceil(duration_sec / window_sec))
    sums = [0.0] * total_windows
    counts = [0] * total_windows
    samples = array("h")
    samples.frombytes(proc.stdout)
    if samples.itemsize != 2:
        return [0.0] * total_windows
    if _is_big_endian():
        samples.byteswap()

    samples_per_window = max(1, int(sample_rate * window_sec))
    for sample_index, sample in enumerate(samples):
        bucket = min(total_windows - 1, sample_index // samples_per_window)
        normalized = sample / 32768
        sums[bucket] += normalized * normalized
        counts[bucket] += 1

    rms = [
        math.sqrt(sums[i] / counts[i]) if counts[i] else 0
        for i in range(total_windows)
    ]
    return _normalize_scores(rms)


def _normalize_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    low = _quantile(values, 0.10)
    high = _quantile(values, 0.95)
    if math.isclose(low, high):
        return [0.0 for _ in values]
    return [max(0.0, min(1.0, (value - low) / (high - low))) for value in values]


def _has_ffmpeg() -> bool:
    return _resolve_ffmpeg() is not None


def _resolve_ffmpeg() -> str | None:
    configured = settings.ffmpeg_path
    path = Path(configured)
    if path.is_absolute() or "/" in configured:
        return str(path) if path.exists() else None
    return shutil.which(configured)


def _analysis_timeout(duration_sec: float) -> float:
    return max(30.0, min(600.0, duration_sec * 1.5))


def _is_big_endian() -> bool:
    import sys

    return sys.byteorder == "big"


def run_video_analysis(
    *,
    task_id: str,
    video_id: str,
    project_id: str | None,
    video_path: Path,
    duration_sec: float,
    body: AnalysisParams,
) -> AnalysisResultRead:
    params = params_for_mode(body)
    features = extract_motion_features(video_path, duration_sec)
    segments = detect_play_windows(features, params, duration_sec=duration_sec)
    result = AnalysisResultRead(
        task_id=task_id,
        video_id=video_id,
        project_id=project_id,
        status="completed",
        params=body,
        progress=1,
        duration_sec=duration_sec,
        segments=segments,
    )
    save_analysis_result(result)
    return result


def create_analysis_task_id() -> str:
    return str(uuid.uuid4())


def save_analysis_result(result: AnalysisResultRead) -> None:
    _analysis_dir().mkdir(parents=True, exist_ok=True)
    path = _analysis_dir() / f"{result.task_id}.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def load_analysis_result(task_id: str) -> AnalysisResultRead | None:
    path = _analysis_dir() / f"{task_id}.json"
    if not path.exists():
        return None
    return AnalysisResultRead.model_validate(json.loads(path.read_text(encoding="utf-8")))


def serialize_feature_windows(features: list[FeatureWindow]) -> list[dict[str, Any]]:
    return [asdict(f) for f in features]


def _analysis_dir() -> Path:
    return settings.storage_dir / "analysis"


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return ordered[index]


def _confidence(features: list[FeatureWindow], start: float, end: float, high_threshold: float) -> float:
    in_range = [f.play_score for f in features if f.start_sec >= start and f.end_sec <= end]
    if not in_range:
        return 0.5
    avg = fmean(in_range)
    if high_threshold <= 0:
        return 0.6
    return max(0.45, min(0.96, avg / high_threshold * 0.72))


def _merge_keep_ranges(
    ranges: list[tuple[float, float, list[str], float]],
    merge_gap_sec: float,
) -> list[tuple[float, float, list[str], float]]:
    if not ranges:
        return []
    ranges = sorted(ranges, key=lambda item: item[0])
    merged = [ranges[0]]
    for start, end, reason, confidence in ranges[1:]:
        prev_start, prev_end, prev_reason, prev_confidence = merged[-1]
        if start - prev_end <= merge_gap_sec:
            merged[-1] = (
                prev_start,
                max(prev_end, end),
                sorted(set(prev_reason + reason + ["merged_short_gap"])),
                max(prev_confidence, confidence),
            )
        else:
            merged.append((start, end, reason, confidence))
    return merged


def _with_cut_segments(keep_segments: list[AnalysisSegment], duration_sec: float) -> list[AnalysisSegment]:
    timeline: list[AnalysisSegment] = []
    cursor = 0.0
    for keep in sorted(keep_segments, key=lambda item: item.start_sec):
        if keep.start_sec > cursor:
            timeline.append(
                AnalysisSegment(
                    start_sec=round(cursor, 3),
                    end_sec=round(keep.start_sec, 3),
                    confidence=0.7,
                    reason=["low_activity"],
                    state="cut",
                )
            )
        timeline.append(keep)
        cursor = max(cursor, keep.end_sec)
    if cursor < duration_sec:
        timeline.append(
            AnalysisSegment(
                start_sec=round(cursor, 3),
                end_sec=round(duration_sec, 3),
                confidence=0.7,
                reason=["low_activity"],
                state="cut",
            )
        )
    return [segment for segment in timeline if segment.end_sec > segment.start_sec]
