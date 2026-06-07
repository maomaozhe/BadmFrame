from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Sequence

from badm_model.contracts import ShuttlePoint
from badm_model.rally_state_machine import RallyCandidate


@dataclass(frozen=True)
class RallyRefinerConfig:
    """Tighten rally boundaries by re-running window detection locally
    within each candidate using stricter thresholds.

    The idea: detection thresholds are intentionally loose for recall.
    Once we know a rally exists in an interval, re-apply stricter
    thresholds to trim the tail where false-positive detections linger.
    """

    # Local window parameters (smaller than detection windows for precision)
    local_window_sec: float = 0.5
    local_step_sec: float = 0.25

    # Stricter activity thresholds (only applied within known candidates)
    min_visible_ratio: float = 0.20
    min_motion_px_sec: float = 280.0
    min_spread_px: float = 200.0

    # Pre-match warmup filtering
    pre_match_grace_sec: float = 15.0
    pre_match_max_duration_sec: float = 5.0


def refine_candidates(
    points: Sequence[ShuttlePoint],
    candidates: list[RallyCandidate],
    config: RallyRefinerConfig | None = None,
) -> list[RallyCandidate]:
    """Apply boundary tightening and pre-match filtering to rally candidates."""
    if config is None:
        config = RallyRefinerConfig()
    if not points or not candidates:
        return list(candidates)

    refined = [_tighten_candidate(points, c, config) for c in candidates]
    refined = _filter_pre_match(refined, config)
    return refined


def _tighten_candidate(
    points: Sequence[ShuttlePoint],
    candidate: RallyCandidate,
    config: RallyRefinerConfig,
) -> RallyCandidate:
    """Re-run local window detection within the candidate at stricter thresholds."""
    c_points = [
        p for p in points if candidate.startSec <= p.timeSec <= candidate.endSec
    ]
    if len(c_points) < 3:
        return candidate

    # Generate local windows
    windows = _make_local_windows(c_points, config)

    # Find the last active window → new end
    new_end = candidate.endSec
    for w in reversed(windows):
        if _window_is_active(w, config):
            new_end = w["end"]
            break

    # Find the first active window → new start
    new_start = candidate.startSec
    for w in windows:
        if _window_is_active(w, config):
            new_start = w["start"]
            break

    if new_start >= new_end:
        return candidate

    changed = False
    new_end_reason = list(candidate.endReason)
    new_start_reason = list(candidate.startReason)

    if new_end < candidate.endSec - 0.3:
        new_end_reason.append("refiner_end_tightened")
        changed = True
    if new_start > candidate.startSec + 0.3:
        new_start_reason.append("refiner_start_tightened")
        changed = True

    if not changed:
        return candidate

    return replace(
        candidate,
        startSec=round(new_start, 3),
        endSec=round(new_end, 3),
        endReason=new_end_reason,
        startReason=new_start_reason,
    )


def _make_local_windows(
    points: Sequence[ShuttlePoint],
    config: RallyRefinerConfig,
) -> list[dict]:
    """Generate overlapping windows within the candidate time range."""
    first_sec = points[0].timeSec
    last_sec = points[-1].timeSec
    windows: list[dict] = []
    start = first_sec
    while start < last_sec:
        end = min(start + config.local_window_sec, last_sec)
        win_points = [p for p in points if start <= p.timeSec < end]
        windows.append({
            "start": start,
            "end": end,
            "points": win_points,
        })
        start = round(start + config.local_step_sec, 6)
    return windows


def _window_is_active(win: dict, config: RallyRefinerConfig) -> bool:
    pts = win["points"]
    if not pts:
        return False
    visible = [p for p in pts if p.visible]
    if not visible:
        return False

    visible_ratio = len(visible) / len(pts)
    if visible_ratio < config.min_visible_ratio:
        return False

    motion = _mean_motion_px_sec(visible)
    spread = _spread_px(visible)

    return motion >= config.min_motion_px_sec or spread >= config.min_spread_px


def _mean_motion_px_sec(visible_points: Sequence[ShuttlePoint]) -> float:
    if len(visible_points) < 2:
        return 0.0
    speeds: list[float] = []
    for prev, cur in zip(visible_points, visible_points[1:]):
        dt = cur.timeSec - prev.timeSec
        if dt > 0:
            speeds.append(math.hypot(cur.x - prev.x, cur.y - prev.y) / dt)
    return sum(speeds) / len(speeds) if speeds else 0.0


def _spread_px(visible_points: Sequence[ShuttlePoint]) -> float:
    if len(visible_points) < 2:
        return 0.0
    xs = [p.x for p in visible_points]
    ys = [p.y for p in visible_points]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))


def _filter_pre_match(
    candidates: list[RallyCandidate],
    config: RallyRefinerConfig,
) -> list[RallyCandidate]:
    return [
        c
        for c in candidates
        if not (
            c.endSec <= config.pre_match_grace_sec
            and c.endSec - c.startSec < config.pre_match_max_duration_sec
        )
    ]
