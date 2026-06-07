from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Sequence

from badm_model.contracts import ShuttlePoint


# ── Public data types ──────────────────────────────────────────────


@dataclass(frozen=True)
class RallyCandidate:
    id: str
    startSec: float
    endSec: float
    confidence: float
    startReason: list[str]
    endReason: list[str]
    reviewState: str  # "pending"
    trajectoryStats: dict  # visibleRatio, maxGapSec, directionChanges, meanSpeedPxSec


@dataclass(frozen=True)
class RallyStateResult:
    candidates: list[RallyCandidate]
    sourcePointCount: int


# ── Configuration ──────────────────────────────────────────────────


@dataclass(frozen=True)
class RallyStateConfig:
    """Tunable parameters for the rally state machine."""

    # How many consecutive visible points (roughly) before we consider a rally
    # "active".  Expressed in seconds; converted to frames internally.
    min_active_sec: float = 0.5

    # Maximum gap (seconds) between two visible-point clusters that still counts
    # as the same rally.
    gap_tolerance_sec: float = 0.5

    # After a "RallyEndCandidate" is raised, how long (seconds) without
    # trajectory recovery before we finalize "RallyEnd".
    end_tolerance_sec: float = 1.5

    # Buffer added to the start of each candidate (seconds).
    pre_buffer_sec: float = 0.5

    # Buffer added to the end of each candidate (seconds).
    post_buffer_sec: float = 1.0

    # Fraction of points in a window that must be visible for the segment
    # to be considered "trajectory present" (used for recovery).
    min_visible_ratio: float = 0.3

    # Visible-ratio threshold in the end_tolerance window below which the
    # state machine transitions from RALLY_ACTIVE → RALLY_END_CANDIDATE.
    # Set above TrackNet's typical false-positive rate during breaks (often
    # 20-35%) so the state machine can distinguish real rallies from noise.
    end_visible_ratio: float = 0.4

    # Minimum duration (seconds) for a valid rally.
    min_rally_duration_sec: float = 2.0


# ── Internal state machine ─────────────────────────────────────────


class _State(Enum):
    IDLE = auto()
    RALLY_ACTIVE = auto()
    RALLY_END_CANDIDATE = auto()


@dataclass
class _RallyBuilder:
    start_idx: int = -1
    end_candidate_idx: int = -1
    start_reasons: list[str] = field(default_factory=list)
    end_reasons: list[str] = field(default_factory=list)
    visible_count: int = 0
    total_count: int = 0


# ── Entry point ────────────────────────────────────────────────────


def segment_rallies(
    points: Sequence[ShuttlePoint],
    fps: float,
    *,
    config: RallyStateConfig | None = None,
) -> RallyStateResult:
    """Segment shuttle points into rally candidates using a state machine.

    States:
        IDLE → RALLY_ACTIVE       (sufficient trajectory)
        RALLY_ACTIVE → RALLY_END_CANDIDATE  (long gap / stationary)
        RALLY_END_CANDIDATE → RALLY_ACTIVE  (trajectory resumes quickly)
        RALLY_END_CANDIDATE → IDLE          (end_tolerance exceeded → emit candidate)
    """
    if config is None:
        config = RallyStateConfig()

    n = len(points)
    if n == 0:
        return RallyStateResult(candidates=[], sourcePointCount=0)

    gap_tolerance_frames = max(1, int(config.gap_tolerance_sec * fps))
    end_tolerance_frames = max(1, int(config.end_tolerance_sec * fps))
    min_active_frames = max(1, int(config.min_active_sec * fps))
    min_rally_frames = max(1, int(config.min_rally_duration_sec * fps))

    state = _State.IDLE
    builder = _RallyBuilder()
    candidates: list[RallyCandidate] = []

    # Track last visible index for gap detection
    last_visible_idx = -1

    for i, p in enumerate(points):
        if state == _State.IDLE:
            if p.visible:
                if builder.start_idx < 0:
                    builder.start_idx = i
                    builder.start_reasons = _detect_start_reason(points, i, fps)
                builder.visible_count += 1
                builder.total_count += 1
                last_visible_idx = i
                if builder.visible_count >= min_active_frames:
                    state = _State.RALLY_ACTIVE
            else:
                # Not yet active; reset
                if builder.start_idx >= 0 and i - last_visible_idx > gap_tolerance_frames:
                    builder = _RallyBuilder()
                    last_visible_idx = -1

        elif state == _State.RALLY_ACTIVE:
            builder.total_count += 1
            if p.visible:
                builder.visible_count += 1
                last_visible_idx = i

            # Windowed visible-ratio end detection.
            # Only check once we have at least end_tolerance_frames of history
            # in this rally, so the window is fully populated.
            if i - builder.start_idx >= end_tolerance_frames:
                window_visible = sum(
                    1 for j in range(i - end_tolerance_frames + 1, i + 1)
                    if points[j].visible
                )
                if window_visible / end_tolerance_frames < config.end_visible_ratio:
                    state = _State.RALLY_END_CANDIDATE
                    builder.end_candidate_idx = i
                    builder.end_reasons = ["low_visible_ratio"]

        elif state == _State.RALLY_END_CANDIDATE:
            builder.total_count += 1
            if p.visible:
                builder.visible_count += 1
                last_visible_idx = i

            # Recovery check: visible ratio in a short recent window.
            # Use min_active_frames as the recovery window size.
            recover_window = min(min_active_frames, i - builder.start_idx + 1)
            recovered = False
            if recover_window > 0:
                recent_visible = sum(
                    1 for j in range(i - recover_window + 1, i + 1)
                    if points[j].visible
                )
                if recent_visible / recover_window >= config.min_visible_ratio:
                    recovered = True

            if recovered and i - builder.end_candidate_idx < end_tolerance_frames:
                # Genuine recovery within tolerance — ball consistently visible again
                builder.end_candidate_idx = -1
                builder.end_reasons = []
                state = _State.RALLY_ACTIVE
                continue

            # Finalize when end_tolerance has elapsed since end_candidate began.
            if i - builder.end_candidate_idx >= end_tolerance_frames:
                candidates.append(_finalize_candidate(points, builder, fps, config))
                if p.visible and recovered:
                    # New rally detected after expiry — start fresh
                    builder = _RallyBuilder()
                    builder.start_idx = i
                    builder.start_reasons = _detect_start_reason(points, i, fps)
                    builder.visible_count = 1
                    builder.total_count = 1
                    last_visible_idx = i
                    state = _State.RALLY_ACTIVE
                else:
                    builder = _RallyBuilder()
                    last_visible_idx = -1
                    state = _State.IDLE

    # Handle trailing rally
    if builder.start_idx >= 0 and builder.end_candidate_idx >= 0:
        candidates.append(_finalize_candidate(points, builder, fps, config))
    elif builder.start_idx >= 0 and state in (_State.RALLY_ACTIVE,):
        # Still active at end of video
        builder.end_candidate_idx = n - 1
        builder.end_reasons = ["end_of_video"]
        candidates.append(_finalize_candidate(points, builder, fps, config))

    # Filter by min duration
    candidates = [c for c in candidates if c.endSec - c.startSec >= config.min_rally_duration_sec]

    # Re-index IDs
    candidates = [
        RallyCandidate(
            id=f"rally-{i + 1:03d}",
            startSec=c.startSec,
            endSec=c.endSec,
            confidence=c.confidence,
            startReason=c.startReason,
            endReason=c.endReason,
            reviewState=c.reviewState,
            trajectoryStats=c.trajectoryStats,
        )
        for i, c in enumerate(candidates)
    ]

    return RallyStateResult(candidates=candidates, sourcePointCount=n)


# ── Helpers ────────────────────────────────────────────────────────


def _finalize_candidate(
    points: Sequence[ShuttlePoint],
    builder: _RallyBuilder,
    fps: float,
    config: RallyStateConfig,
) -> RallyCandidate:
    start_idx = builder.start_idx
    end_idx = min(builder.end_candidate_idx, len(points) - 1)

    # Apply pre/post buffers
    pre_frames = int(config.pre_buffer_sec * fps)
    post_frames = int(config.post_buffer_sec * fps)
    buffered_start = max(0, start_idx - pre_frames)
    buffered_end = min(len(points) - 1, end_idx + post_frames)

    start_sec = points[buffered_start].timeSec
    end_sec = points[buffered_end].timeSec

    # Compute trajectory stats over the rally segment
    seg_points = points[start_idx : end_idx + 1]
    stats = _compute_segment_stats(seg_points, fps)

    # Confidence heuristic
    confidence = _confidence(stats, builder)

    return RallyCandidate(
        id="",  # assigned later
        startSec=round(start_sec, 3),
        endSec=round(end_sec, 3),
        confidence=round(confidence, 4),
        startReason=list(builder.start_reasons) if builder.start_reasons else ["trajectory_appeared"],
        endReason=list(builder.end_reasons) if builder.end_reasons else ["trajectory_lost"],
        reviewState="pending",
        trajectoryStats=stats,
    )


def _compute_segment_stats(points: Sequence[ShuttlePoint], fps: float) -> dict:
    visible_pts = [p for p in points if p.visible]
    total = len(points)
    if total == 0:
        return {"visibleRatio": 0.0, "maxGapSec": 0.0, "directionChanges": 0, "meanSpeedPxSec": 0.0}

    visible_ratio = len(visible_pts) / total
    max_gap_sec = _longest_gap_sec(points)
    dir_changes = _count_direction_changes(visible_pts)
    mean_speed = _mean_speed_px_sec(visible_pts, fps)
    return {
        "visibleRatio": round(visible_ratio, 4),
        "maxGapSec": round(max_gap_sec, 4),
        "directionChanges": dir_changes,
        "meanSpeedPxSec": round(mean_speed, 1),
    }


def _confidence(stats: dict, builder: _RallyBuilder) -> float:
    """Heuristic confidence: high visible ratio + low gap = high confidence."""
    vr = stats.get("visibleRatio", 0.0)
    mg = stats.get("maxGapSec", 99.0)
    gap_penalty = min(1.0, mg / 3.0)  # 3 sec gap → full penalty
    return round(max(0.0, vr * (1.0 - gap_penalty)), 4)


def _detect_start_reason(points: Sequence[ShuttlePoint], idx: int, fps: float) -> list[str]:
    reasons: list[str] = []
    p = points[idx]
    # Heuristic: ball near bottom half (serve position) or previously stationary
    if p.y > 400:
        reasons.append("near_net_or_serve_zone")
    reasons.append("continuous_trajectory")
    return reasons


def _longest_gap_sec(points: Sequence[ShuttlePoint]) -> float:
    max_gap = 0.0
    gap_start: float | None = None
    for p in points:
        if not p.visible:
            if gap_start is None:
                gap_start = p.timeSec
        else:
            if gap_start is not None:
                max_gap = max(max_gap, p.timeSec - gap_start)
                gap_start = None
    return max_gap


def _count_direction_changes(visible_points: list[ShuttlePoint]) -> int:
    changes = 0
    for i in range(1, len(visible_points) - 1):
        dx1 = visible_points[i].x - visible_points[i - 1].x
        dy1 = visible_points[i].y - visible_points[i - 1].y
        dx2 = visible_points[i + 1].x - visible_points[i].x
        dy2 = visible_points[i + 1].y - visible_points[i].y
        dot = dx1 * dx2 + dy1 * dy2
        if dot < 0:  # angle > 90 deg
            changes += 1
    return changes


def _mean_speed_px_sec(visible_points: list[ShuttlePoint], fps: float) -> float:
    if len(visible_points) < 2:
        return 0.0
    speeds = []
    for i in range(1, len(visible_points)):
        dx = visible_points[i].x - visible_points[i - 1].x
        dy = visible_points[i].y - visible_points[i - 1].y
        df = visible_points[i].frameIndex - visible_points[i - 1].frameIndex
        if df > 0:
            speeds.append((dx**2 + dy**2) ** 0.5 / df * fps)
    return sum(speeds) / len(speeds) if speeds else 0.0
