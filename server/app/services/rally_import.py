from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.rally import RallyCandidateRead


def load_rally_candidates(path: Path) -> list[RallyCandidateRead]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_rally_candidates_payload(payload)


def parse_rally_candidates_payload(payload: dict[str, Any]) -> list[RallyCandidateRead]:
    items = payload.get("candidates")
    if not isinstance(items, list):
        raise ValueError("Expected candidates to be a list.")

    default_source = payload.get("source", "imported-json")
    candidates = [_candidate_from_payload(item, index, default_source=default_source) for index, item in enumerate(items, 1)]
    return sorted(candidates, key=lambda candidate: candidate.start_sec)


def _candidate_from_payload(item: dict[str, Any], index: int, *, default_source: str) -> RallyCandidateRead:
    if not isinstance(item, dict):
        raise ValueError("Expected each candidate to be a JSON object.")

    return RallyCandidateRead(
        id=str(_value(item, "id", default=f"rally-{index:03d}")),
        start_sec=float(_value(item, "start_sec", "startSec")),
        end_sec=float(_value(item, "end_sec", "endSec")),
        confidence=float(_value(item, "confidence")),
        review_state=_value(item, "review_state", "reviewState", default="pending"),
        start_reason=list(_value(item, "start_reason", "startReason", default=[])),
        end_reason=list(_value(item, "end_reason", "endReason", default=[])),
        source=_value(item, "source", default=default_source),
        trajectory_stats=_trajectory_stats(item.get("trajectory_stats") or item.get("trajectoryStats")),
    )


def _trajectory_stats(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Expected trajectoryStats to be a JSON object.")
    return {
        "visible_ratio": value.get("visible_ratio", value.get("visibleRatio")),
        "max_gap_sec": value.get("max_gap_sec", value.get("maxGapSec")),
        "direction_changes": value.get("direction_changes", value.get("directionChanges")),
        "mean_speed_px_sec": value.get("mean_speed_px_sec", value.get("meanSpeedPxSec")),
    }


def _value(item: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in item:
            return item[name]
    if default is not None:
        return default
    raise ValueError(f"Missing required field. Expected one of: {', '.join(names)}")
