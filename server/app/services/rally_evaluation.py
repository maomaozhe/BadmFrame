from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class RallyInterval:
    id: str
    start_sec: float
    end_sec: float

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec


@dataclass(frozen=True)
class RallyEvaluation:
    total_rallies: int
    total_candidates: int
    matched_rallies: int
    missed_rallies: int
    false_rallies: int
    merged_rallies: int
    mean_start_error_sec: float
    mean_end_error_sec: float


@dataclass(frozen=True)
class _RallyMatch:
    rally_id: str
    candidate_id: str
    overlap_sec: float
    start_error_sec: float
    end_error_sec: float


def load_annotations(path: Path) -> list[RallyInterval]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = _interval_items(data, preferred_keys=("rallies", "annotations"))
    return [_coerce_interval(item, "rally", index) for index, item in enumerate(items, 1)]


def evaluate_candidates(
    annotations: Iterable[RallyInterval],
    candidates: Iterable[Any],
    overlap_threshold: float = 0.3,
) -> RallyEvaluation:
    normalized_annotations = [_coerce_interval(item, "rally", index) for index, item in enumerate(annotations, 1)]
    normalized_candidates = [_coerce_interval(item, "candidate", index) for index, item in enumerate(candidates, 1)]

    matches_by_rally: dict[str, list[_RallyMatch]] = {item.id: [] for item in normalized_annotations}
    matches_by_candidate: dict[str, list[_RallyMatch]] = {item.id: [] for item in normalized_candidates}

    for rally in normalized_annotations:
        for candidate in normalized_candidates:
            overlap_sec = _overlap_sec(rally, candidate)
            if overlap_sec <= 0:
                continue
            if overlap_sec / rally.duration_sec < overlap_threshold:
                continue

            match = _RallyMatch(
                rally_id=rally.id,
                candidate_id=candidate.id,
                overlap_sec=round(overlap_sec, 3),
                start_error_sec=round(abs(candidate.start_sec - rally.start_sec), 3),
                end_error_sec=round(abs(candidate.end_sec - rally.end_sec), 3),
            )
            matches_by_rally[rally.id].append(match)
            matches_by_candidate[candidate.id].append(match)

    matched_rallies = [rally for rally in normalized_annotations if matches_by_rally[rally.id]]
    missed_rallies = [rally for rally in normalized_annotations if not matches_by_rally[rally.id]]
    false_rallies = [candidate for candidate in normalized_candidates if not matches_by_candidate[candidate.id]]
    merged_rallies = [
        candidate
        for candidate in normalized_candidates
        if len({match.rally_id for match in matches_by_candidate[candidate.id]}) > 1
    ]
    best_matches = [_best_match(matches_by_rally[rally.id]) for rally in matched_rallies]

    return RallyEvaluation(
        total_rallies=len(normalized_annotations),
        total_candidates=len(normalized_candidates),
        matched_rallies=len(matched_rallies),
        missed_rallies=len(missed_rallies),
        false_rallies=len(false_rallies),
        merged_rallies=len(merged_rallies),
        mean_start_error_sec=_mean(match.start_error_sec for match in best_matches),
        mean_end_error_sec=_mean(match.end_error_sec for match in best_matches),
    )


def _interval_items(data: Any, *, preferred_keys: tuple[str, ...]) -> list[Any]:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object or array of intervals.")
    for key in preferred_keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    raise ValueError(f"Expected one of these interval arrays: {', '.join(preferred_keys)}")


def _coerce_interval(item: Any, prefix: str, index: int) -> RallyInterval:
    if isinstance(item, RallyInterval):
        interval = item
    else:
        interval = RallyInterval(
            id=str(_value(item, "id", default=f"{prefix}-{index:03d}")),
            start_sec=float(_value(item, "start_sec", "startSec")),
            end_sec=float(_value(item, "end_sec", "endSec")),
        )
    if interval.end_sec <= interval.start_sec:
        raise ValueError(f"{prefix} interval must end after it starts: {interval}")
    return interval


def _value(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
        if not isinstance(item, dict) and hasattr(item, name):
            return getattr(item, name)
    if default is not None:
        return default
    raise ValueError(f"Missing required field. Expected one of: {', '.join(names)}")


def _overlap_sec(a: RallyInterval, b: RallyInterval) -> float:
    return max(0.0, min(a.end_sec, b.end_sec) - max(a.start_sec, b.start_sec))


def _best_match(matches: list[_RallyMatch]) -> _RallyMatch:
    return max(matches, key=lambda match: (match.overlap_sec, -match.start_error_sec - match.end_error_sec))


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        return 0
    return round(sum(items) / len(items), 3)
