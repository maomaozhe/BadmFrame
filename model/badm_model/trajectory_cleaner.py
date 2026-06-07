from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from badm_model.contracts import ShuttlePoint


@dataclass(frozen=True)
class TrajectoryGap:
    start: ShuttlePoint
    end: ShuttlePoint
    lengthFrames: int
    lengthSec: float


@dataclass(frozen=True)
class CleanedTrajectory:
    points: list[ShuttlePoint]
    gaps: list[TrajectoryGap]
    originalCount: int
    removedCount: int


def clean_trajectory(
    points: Sequence[ShuttlePoint],
    *,
    max_gap_frames: int = 10,
    max_speed_px_per_frame: float = 200.0,
    court_margin_px: int = 100,
    frame_width: int | None = None,
    frame_height: int | None = None,
) -> CleanedTrajectory:
    """Clean raw TrackNetV3 trajectory points.

    Steps:
      1. Clamp coordinates that stray far outside the frame + margin.
      2. Mark physically-impossible speed jumps as invisible.
      3. Fill short gaps (<= max_gap_frames consecutive invisible frames)
         with linearly-interpolated points.

    Args:
        points: Raw shuttle points from TrackNetV3, sorted by frameIndex.
        max_gap_frames: Maximum consecutive invisible frames to fill via interpolation.
        max_speed_px_per_frame: Maximum plausible ball speed in pixels per frame.
        court_margin_px: Margin beyond frame bounds to tolerate.
        frame_width: Expected frame width; if given, points beyond width + margin are clamped.
        frame_height: Expected frame height; if given, points beyond height + margin are clamped.
    """
    if not points:
        return CleanedTrajectory(points=[], gaps=[], originalCount=0, removedCount=0)

    original_count = len(points)
    cleaned = list(points)
    removed = 0

    # --- 1. Clamp out-of-bounds coordinates ---
    if frame_width is not None:
        max_x = frame_width + court_margin_px
        for i, p in enumerate(cleaned):
            if p.visible and (p.x < -court_margin_px or p.x > max_x):
                cleaned[i] = _invisible(p)
                removed += 1
    if frame_height is not None:
        max_y = frame_height + court_margin_px
        for i, p in enumerate(cleaned):
            if p.visible and (p.y < -court_margin_px or p.y > max_y):
                cleaned[i] = _invisible(p)
                removed += 1

    # --- 2. Filter speed outliers ---
    cleaned = _filter_speed_outliers(cleaned, max_speed_px_per_frame)

    # --- 3. Fill short gaps ---
    filled, gaps = _fill_short_gaps(cleaned, max_gap_frames)
    return CleanedTrajectory(
        points=filled,
        gaps=gaps,
        originalCount=original_count,
        removedCount=removed,
    )


def _invisible(p: ShuttlePoint) -> ShuttlePoint:
    return ShuttlePoint(
        frameIndex=p.frameIndex,
        timeSec=p.timeSec,
        x=0.0,
        y=0.0,
        confidence=0.0,
        visible=False,
    )


def _filter_speed_outliers(
    points: list[ShuttlePoint],
    max_speed_px_per_frame: float,
) -> list[ShuttlePoint]:
    """Mark points as invisible when the inter-frame speed exceeds the threshold."""
    cleaned = list(points)
    # Find previous visible point for each visible point
    prev_visible_idx = -1
    for i, p in enumerate(cleaned):
        if not p.visible:
            continue
        if prev_visible_idx >= 0:
            prev = cleaned[prev_visible_idx]
            dx = p.x - prev.x
            dy = p.y - prev.y
            df = p.frameIndex - prev.frameIndex
            if df > 0:
                speed = (dx**2 + dy**2) ** 0.5 / df
                if speed > max_speed_px_per_frame:
                    cleaned[i] = _invisible(p)
                    continue
        prev_visible_idx = i
    return cleaned


def _fill_short_gaps(
    points: list[ShuttlePoint],
    max_gap_frames: int,
) -> tuple[list[ShuttlePoint], list[TrajectoryGap]]:
    """Fill short invisible gaps with linearly-interpolated visible points."""
    if not points:
        return points, []

    filled: list[ShuttlePoint] = []
    gaps: list[TrajectoryGap] = []
    idx = 0

    while idx < len(points):
        p = points[idx]
        if p.visible:
            filled.append(p)
            idx += 1
            continue

        # Start of an invisible segment
        gap_start_idx = idx
        while idx < len(points) and not points[idx].visible:
            idx += 1
        # idx now points to first visible after gap (or end)

        if idx >= len(points):
            # Trailing invisible segment; keep as-is
            for j in range(gap_start_idx, len(points)):
                filled.append(points[j])
            break

        gap_end_idx = idx  # the visible point after the gap
        gap_length = gap_end_idx - gap_start_idx

        if gap_start_idx == 0:
            # Leading invisible segment (no visible anchor before); keep as-is
            for j in range(gap_start_idx, gap_end_idx):
                filled.append(points[j])
            filled.append(points[gap_end_idx])
            idx += 1
            continue

        prev_visible = filled[-1]  # last visible in filled list
        next_visible = points[gap_end_idx]

        gaps.append(
            TrajectoryGap(
                start=prev_visible,
                end=next_visible,
                lengthFrames=gap_length,
                lengthSec=round(next_visible.timeSec - prev_visible.timeSec, 6),
            )
        )

        if gap_length <= max_gap_frames:
            # Fill with interpolated points
            for t in range(1, gap_length + 1):
                frac = t / (gap_length + 1)
                interp_frame = prev_visible.frameIndex + t
                interp_time = round(prev_visible.timeSec + frac * (next_visible.timeSec - prev_visible.timeSec), 6)
                interp_x = round(prev_visible.x + frac * (next_visible.x - prev_visible.x), 1)
                interp_y = round(prev_visible.y + frac * (next_visible.y - prev_visible.y), 1)
                filled.append(
                    ShuttlePoint(
                        frameIndex=interp_frame,
                        timeSec=interp_time,
                        x=interp_x,
                        y=interp_y,
                        confidence=0.5,
                        visible=True,
                    )
                )
        else:
            # Gap too large; keep as invisible
            for j in range(gap_start_idx, gap_end_idx):
                filled.append(points[j])
        # Add the anchor visible point
        filled.append(next_visible)
        idx += 1

    return filled, gaps
