from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Iterable, Sequence

from badm_model.contracts import ShuttlePoint
from badm_model.rally_refiner import RallyRefinerConfig, refine_candidates
from badm_model.rally_state_machine import RallyCandidate


@dataclass(frozen=True)
class WindowSegmentationConfig:
    window_sec: float = 1.0
    step_sec: float = 0.5
    min_visible_ratio: float = 0.3
    min_motion_px_sec: float = 100.0
    min_spread_px: float = 80.0
    merge_gap_sec: float = 1.5
    min_rally_duration_sec: float = 2.0
    pre_buffer_sec: float = 0.5
    post_buffer_sec: float = 0.5
    start_sec: float = 0.0
    end_sec: float | None = None


@dataclass(frozen=True)
class WindowTuningResult:
    config: WindowSegmentationConfig
    candidates: list[RallyCandidate]
    report: dict[str, Any]
    refiner_config: RallyRefinerConfig | None = None


@dataclass(frozen=True)
class _WindowFeature:
    startSec: float
    endSec: float
    visibleRatio: float
    meanMotionPxSec: float
    spreadPx: float
    visibleCount: int


def generate_window_candidates(
    points: Sequence[ShuttlePoint],
    fps: float,
    config: WindowSegmentationConfig | None = None,
) -> list[RallyCandidate]:
    if config is None:
        config = WindowSegmentationConfig()
    if not points:
        return []

    windows = _extract_windows(points, config)
    return _generate_candidates_from_windows(windows, config)


def _generate_candidates_from_windows(
    windows: Sequence[_WindowFeature],
    config: WindowSegmentationConfig,
) -> list[RallyCandidate]:
    active = [
        feature
        for feature in windows
        if feature.visibleRatio >= config.min_visible_ratio
        and (
            feature.meanMotionPxSec >= config.min_motion_px_sec
            or feature.spreadPx >= config.min_spread_px
        )
    ]
    intervals = _merge_windows(active, config)
    intervals = [
        (start, end)
        for start, end in intervals
        if end - start >= config.min_rally_duration_sec
    ]
    return [_interval_to_candidate(index, start, end, config) for index, (start, end) in enumerate(intervals, 1)]


def tune_window_segmentation(
    points: Sequence[ShuttlePoint],
    fps: float,
    *,
    annotations: list[dict[str, Any]],
    base_config: WindowSegmentationConfig | None = None,
    refiner_config: RallyRefinerConfig | None = None,
    min_visible_ratio_grid: Iterable[float] = (0.1, 0.15, 0.2, 0.25, 0.3, 0.35),
    min_motion_grid: Iterable[float] = (80.0, 120.0, 160.0, 220.0, 300.0),
    min_spread_grid: Iterable[float] = (40.0, 70.0, 100.0, 140.0, 180.0),
    merge_gap_grid: Iterable[float] = (0.5, 0.8, 1.0, 1.5, 2.0),
    pre_buffer_grid: Iterable[float] = (0.0, 0.25, 0.5),
    post_buffer_grid: Iterable[float] = (0.0, 0.5, 1.0),
) -> WindowTuningResult:
    if base_config is None:
        base_config = WindowSegmentationConfig()

    best: WindowTuningResult | None = None
    best_score: tuple[float, ...] | None = None
    windows = _extract_windows(points, base_config)

    for min_visible_ratio in min_visible_ratio_grid:
        for min_motion in min_motion_grid:
            for min_spread in min_spread_grid:
                for merge_gap in merge_gap_grid:
                    for pre_buffer in pre_buffer_grid:
                        for post_buffer in post_buffer_grid:
                            config = replace(
                                base_config,
                                min_visible_ratio=min_visible_ratio,
                                min_motion_px_sec=min_motion,
                                min_spread_px=min_spread,
                                merge_gap_sec=merge_gap,
                                pre_buffer_sec=pre_buffer,
                                post_buffer_sec=post_buffer,
                            )
                            candidates = _generate_candidates_from_windows(windows, config)
                            if refiner_config is not None:
                                candidates = refine_candidates(points, candidates, refiner_config)
                            report = evaluate_candidate_intervals(annotations, candidates)
                            score = _score_report(report, len(annotations))
                            if best_score is None or score > best_score:
                                best_score = score
                                best = WindowTuningResult(
                                    config=config,
                                    candidates=candidates,
                                    report=report,
                                    refiner_config=refiner_config,
                                )

    if best is None:
        return WindowTuningResult(
            config=base_config,
            candidates=[],
            report=evaluate_candidate_intervals(annotations, []),
        )
    return best


def evaluate_candidate_intervals(
    annotations: list[dict[str, Any]],
    candidates: Sequence[RallyCandidate],
    *,
    min_annotation_overlap: float = 0.4,
) -> dict[str, Any]:
    normalized_annotations = [_normalize_interval(item, "rally", index) for index, item in enumerate(annotations, 1)]
    normalized_candidates = [
        _normalize_interval(
            {"id": item.id, "startSec": item.startSec, "endSec": item.endSec},
            "candidate",
            index,
        )
        for index, item in enumerate(candidates, 1)
    ]

    matches_by_rally = {item["id"]: [] for item in normalized_annotations}
    matches_by_candidate = {item["id"]: [] for item in normalized_candidates}

    for rally in normalized_annotations:
        for candidate in normalized_candidates:
            overlap_sec = _overlap_sec(rally, candidate)
            if overlap_sec <= 0 or overlap_sec / rally["durationSec"] < min_annotation_overlap:
                continue
            match = {
                "rallyId": rally["id"],
                "candidateId": candidate["id"],
                "overlapSec": round(overlap_sec, 3),
                "annotationOverlap": round(overlap_sec / rally["durationSec"], 4),
                "candidateOverlap": round(overlap_sec / candidate["durationSec"], 4),
                "startErrorSec": round(abs(candidate["startSec"] - rally["startSec"]), 3),
                "endErrorSec": round(abs(candidate["endSec"] - rally["endSec"]), 3),
            }
            matches_by_rally[rally["id"]].append(match)
            matches_by_candidate[candidate["id"]].append(match)

    matched_rallies = [rally for rally in normalized_annotations if matches_by_rally[rally["id"]]]
    missed_rallies = [rally for rally in normalized_annotations if not matches_by_rally[rally["id"]]]
    matched_candidates = [candidate for candidate in normalized_candidates if matches_by_candidate[candidate["id"]]]
    false_positive_candidates = [candidate for candidate in normalized_candidates if not matches_by_candidate[candidate["id"]]]
    merged_candidates = [
        candidate for candidate in normalized_candidates if len({match["rallyId"] for match in matches_by_candidate[candidate["id"]]}) > 1
    ]
    fragmented_rallies = [
        rally for rally in normalized_annotations if len({match["candidateId"] for match in matches_by_rally[rally["id"]]}) > 1
    ]
    best_matches = [_best_match(matches_by_rally[rally["id"]]) for rally in matched_rallies]
    average_start_error = _average([match["startErrorSec"] for match in best_matches])
    average_end_error = _average([match["endErrorSec"] for match in best_matches])

    return {
        "totalRallies": len(normalized_annotations),
        "totalCandidates": len(normalized_candidates),
        "matchedRallies": len(matched_rallies),
        "missedRallies": len(missed_rallies),
        "missedRallyIds": [item["id"] for item in missed_rallies],
        "falsePositives": len(false_positive_candidates),
        "falsePositiveCandidateIds": [item["id"] for item in false_positive_candidates],
        "mergedCandidates": len(merged_candidates),
        "mergedCandidateIds": [item["id"] for item in merged_candidates],
        "fragmentedRallies": len(fragmented_rallies),
        "fragmentedRallyIds": [item["id"] for item in fragmented_rallies],
        "recall": _ratio(len(matched_rallies), len(normalized_annotations)),
        "precision": _ratio(len(matched_candidates), len(normalized_candidates)),
        "boundaryErrorSec": {
            "averageStart": average_start_error,
            "averageEnd": average_end_error,
            "averageTotal": round(average_start_error + average_end_error, 3),
        },
        "matches": best_matches,
    }


def _extract_windows(points: Sequence[ShuttlePoint], config: WindowSegmentationConfig) -> list[_WindowFeature]:
    first_sec = max(config.start_sec, points[0].timeSec)
    last_sec = min(config.end_sec if config.end_sec is not None else points[-1].timeSec, points[-1].timeSec)
    if last_sec <= first_sec:
        return []

    windows: list[_WindowFeature] = []
    start = first_sec
    while start < last_sec:
        end = min(start + config.window_sec, last_sec)
        window_points = [p for p in points if start <= p.timeSec < end]
        windows.append(_feature_for_window(start, end, window_points))
        start = round(start + config.step_sec, 6)
    return windows


def _feature_for_window(start: float, end: float, points: Sequence[ShuttlePoint]) -> _WindowFeature:
    visible = [p for p in points if p.visible]
    visible_ratio = len(visible) / len(points) if points else 0.0
    mean_motion = _mean_motion_px_sec(visible)
    spread = _spread_px(visible)
    return _WindowFeature(
        startSec=round(start, 3),
        endSec=round(end, 3),
        visibleRatio=round(visible_ratio, 4),
        meanMotionPxSec=round(mean_motion, 3),
        spreadPx=round(spread, 3),
        visibleCount=len(visible),
    )


def _merge_windows(
    windows: Sequence[_WindowFeature],
    config: WindowSegmentationConfig,
) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    current_start: float | None = None
    current_end: float | None = None

    for window in windows:
        if current_start is None:
            current_start = window.startSec
            current_end = window.endSec
            continue
        assert current_end is not None
        if window.startSec - current_end <= config.merge_gap_sec:
            current_end = max(current_end, window.endSec)
        else:
            intervals.append(_buffer_interval(current_start, current_end, config))
            current_start = window.startSec
            current_end = window.endSec

    if current_start is not None and current_end is not None:
        intervals.append(_buffer_interval(current_start, current_end, config))
    return intervals


def _buffer_interval(start: float, end: float, config: WindowSegmentationConfig) -> tuple[float, float]:
    buffered_start = max(config.start_sec, start - config.pre_buffer_sec)
    buffered_end = end + config.post_buffer_sec
    if config.end_sec is not None:
        buffered_end = min(config.end_sec, buffered_end)
    return round(buffered_start, 3), round(buffered_end, 3)


def _interval_to_candidate(
    index: int,
    start: float,
    end: float,
    config: WindowSegmentationConfig,
) -> RallyCandidate:
    return RallyCandidate(
        id=f"rally-{index:03d}",
        startSec=round(start, 3),
        endSec=round(end, 3),
        confidence=1.0,
        startReason=["window_motion_active"],
        endReason=["window_motion_inactive"],
        reviewState="pending",
        trajectoryStats={
            "windowSec": config.window_sec,
            "stepSec": config.step_sec,
            "minVisibleRatio": config.min_visible_ratio,
            "minMotionPxSec": config.min_motion_px_sec,
            "minSpreadPx": config.min_spread_px,
            "mergeGapSec": config.merge_gap_sec,
        },
    )


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


def _normalize_interval(item: dict[str, Any], prefix: str, index: int) -> dict[str, Any]:
    start = float(item.get("startSec", item.get("start_sec")))
    end = float(item.get("endSec", item.get("end_sec")))
    return {
        "id": str(item.get("id") or f"{prefix}-{index:03d}"),
        "startSec": start,
        "endSec": end,
        "durationSec": end - start,
    }


def _overlap_sec(a: dict[str, Any], b: dict[str, Any]) -> float:
    return max(0.0, min(a["endSec"], b["endSec"]) - max(a["startSec"], b["startSec"]))


def _best_match(matches: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        matches,
        key=lambda match: (
            match["overlapSec"],
            -match["startErrorSec"] - match["endErrorSec"],
        ),
    )


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _score_report(report: dict[str, Any], annotation_count: int) -> tuple[float, ...]:
    boundary = report["boundaryErrorSec"]["averageTotal"]
    return (
        report["recall"],
        -report["mergedCandidates"],
        -report["fragmentedRallies"],
        -boundary,
        report["precision"],
        -abs(report["totalCandidates"] - annotation_count),
        -report["falsePositives"],
    )
