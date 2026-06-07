from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from badm_model.contracts import ShuttlePoint


@dataclass(frozen=True)
class FrameFeature:
    frameIndex: int
    timeSec: float
    visible: bool
    x: float
    y: float
    # Windowed features
    visibleRatio: float
    maxGapSec: float
    directionChanges: int
    meanSpeedPxSec: float
    # Derived signals
    nearBoundary: bool
    isStationary: bool


@dataclass(frozen=True)
class TrajectoryFeatures:
    features: list[FrameFeature]
    fps: float


def extract_features(
    points: Sequence[ShuttlePoint],
    fps: float,
    *,
    window_frames: int = 30,
    stationary_speed_threshold: float = 50.0,
    direction_change_angle_deg: float = 30.0,
    boundary_range_sec: float = 14.0,
) -> TrajectoryFeatures:
    """Extract per-frame trajectory features using a sliding window.

    Args:
        points: Cleaned shuttle points sorted by frameIndex.
        fps: Frames per second of the source video.
        window_frames: Sliding window size in frames (centered on each point).
        stationary_speed_threshold: Speed in px/sec below which the ball is
            considered stationary (e.g., held in hand).
        direction_change_angle_deg: Minimum angle change (degrees) to count
            as a direction change.
        boundary_range_sec: Number of seconds to look ahead/behind when
            determining if current point is near a trajectory boundary
            (start or end of a continuous visible segment).
    """
    if not points:
        return TrajectoryFeatures(features=[], fps=fps)

    n = len(points)
    half_window = window_frames // 2
    features: list[FrameFeature] = []

    for i, p in enumerate(points):
        lo = max(0, i - half_window)
        hi = min(n, i + half_window + 1)
        window = [pts for pts in points[lo:hi] if pts.visible]

        # visibleRatio
        window_len = hi - lo
        visible_ratio = len(window) / window_len if window_len > 0 else 0.0

        # maxGapSec
        max_gap_sec = _max_visible_gap(points[lo:hi])

        # directionChanges
        dir_changes = _count_direction_changes(window, direction_change_angle_deg)

        # meanSpeedPxSec
        mean_speed = _mean_speed(window, fps)

        # nearBoundary
        near_boundary = _is_near_boundary(points, i, boundary_range_sec, fps)

        # isStationary
        is_stationary = mean_speed < stationary_speed_threshold

        features.append(
            FrameFeature(
                frameIndex=p.frameIndex,
                timeSec=p.timeSec,
                visible=p.visible,
                x=p.x,
                y=p.y,
                visibleRatio=round(visible_ratio, 4),
                maxGapSec=round(max_gap_sec, 4),
                directionChanges=dir_changes,
                meanSpeedPxSec=round(mean_speed, 1),
                nearBoundary=near_boundary,
                isStationary=is_stationary,
            )
        )

    return TrajectoryFeatures(features=features, fps=fps)


def _max_visible_gap(points: Sequence[ShuttlePoint]) -> float:
    """Measure the longest continuous invisible span (in seconds)."""
    max_gap = 0.0
    gap_start_sec: float | None = None
    for p in points:
        if not p.visible:
            if gap_start_sec is None:
                gap_start_sec = p.timeSec
        else:
            if gap_start_sec is not None:
                gap_dur = p.timeSec - gap_start_sec
                if gap_dur > max_gap:
                    max_gap = gap_dur
                gap_start_sec = None
    return max_gap


def _count_direction_changes(
    visible_points: list[ShuttlePoint],
    angle_threshold_deg: float,
) -> int:
    """Count direction reversals based on dot-product angle."""
    if len(visible_points) < 3:
        return 0
    cos_thresh = math.cos(math.radians(angle_threshold_deg))
    changes = 0
    for i in range(1, len(visible_points) - 1):
        dx1 = visible_points[i].x - visible_points[i - 1].x
        dy1 = visible_points[i].y - visible_points[i - 1].y
        dx2 = visible_points[i + 1].x - visible_points[i].x
        dy2 = visible_points[i + 1].y - visible_points[i].y
        mag1 = math.sqrt(dx1**2 + dy1**2)
        mag2 = math.sqrt(dx2**2 + dy2**2)
        if mag1 < 1e-6 or mag2 < 1e-6:
            continue
        cos_angle = (dx1 * dx2 + dy1 * dy2) / (mag1 * mag2)
        if cos_angle < cos_thresh:
            changes += 1
    return changes


def _mean_speed(visible_points: list[ShuttlePoint], fps: float) -> float:
    """Average inter-frame speed in px/sec among visible points."""
    if len(visible_points) < 2:
        return 0.0
    speeds: list[float] = []
    for i in range(1, len(visible_points)):
        dx = visible_points[i].x - visible_points[i - 1].x
        dy = visible_points[i].y - visible_points[i - 1].y
        df = visible_points[i].frameIndex - visible_points[i - 1].frameIndex
        if df > 0:
            speed_px_per_frame = math.sqrt(dx**2 + dy**2) / df
            speeds.append(speed_px_per_frame * fps)
    if not speeds:
        return 0.0
    return sum(speeds) / len(speeds)


def _is_near_boundary(
    points: Sequence[ShuttlePoint],
    idx: int,
    range_sec: float,
    fps: float,
) -> bool:
    """Check if the point at idx is near a visible-segment boundary."""
    range_frames = int(range_sec * fps)
    current_time = points[idx].timeSec

    # Look backward
    lo = max(0, idx - range_frames)
    for j in range(idx - 1, lo - 1, -1):
        if current_time - points[j].timeSec > range_sec:
            break
        if not points[j].visible:
            return True

    # Look forward
    hi = min(len(points), idx + range_frames + 1)
    for j in range(idx + 1, hi):
        if points[j].timeSec - current_time > range_sec:
            break
        if not points[j].visible:
            return True

    return False
