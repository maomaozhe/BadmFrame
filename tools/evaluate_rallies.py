from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_MIN_ANNOTATION_OVERLAP = 0.4


def load_rally_annotations(path: str | Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    return _load_intervals(data, preferred_keys=("rallies", "annotations"))


def load_candidates(path: str | Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    intervals = _load_intervals(data, preferred_keys=("candidates", "rallies", "segments"))
    return [item for item in intervals if item.get("state") != "cut"]


def evaluate_rallies(
    annotations: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    min_annotation_overlap: float = DEFAULT_MIN_ANNOTATION_OVERLAP,
) -> dict[str, Any]:
    normalized_annotations = [_normalize_interval(item, "rally", index) for index, item in enumerate(annotations, 1)]
    normalized_candidates = [_normalize_interval(item, "candidate", index) for index, item in enumerate(candidates, 1)]

    matches_by_rally: dict[str, list[dict[str, Any]]] = {item["id"]: [] for item in normalized_annotations}
    matches_by_candidate: dict[str, list[dict[str, Any]]] = {item["id"]: [] for item in normalized_candidates}

    for rally in normalized_annotations:
        for candidate in normalized_candidates:
            overlap_sec = _overlap_sec(rally, candidate)
            if overlap_sec <= 0:
                continue
            if overlap_sec / rally["durationSec"] < min_annotation_overlap:
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

    total_rallies = len(normalized_annotations)
    total_candidates = len(normalized_candidates)

    return {
        "totalRallies": total_rallies,
        "totalCandidates": total_candidates,
        "matchedRallies": len(matched_rallies),
        "missedRallies": len(missed_rallies),
        "missedRallyIds": [item["id"] for item in missed_rallies],
        "falsePositives": len(false_positive_candidates),
        "falsePositiveCandidateIds": [item["id"] for item in false_positive_candidates],
        "mergedCandidates": len(merged_candidates),
        "mergedCandidateIds": [item["id"] for item in merged_candidates],
        "fragmentedRallies": len(fragmented_rallies),
        "fragmentedRallyIds": [item["id"] for item in fragmented_rallies],
        "recall": _ratio(len(matched_rallies), total_rallies),
        "precision": _ratio(len(matched_candidates), total_candidates),
        "boundaryErrorSec": {
            "averageStart": average_start_error,
            "averageEnd": average_end_error,
            "averageTotal": round(average_start_error + average_end_error, 3),
        },
        "matches": best_matches,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate rally candidate JSON against manual annotations.")
    parser.add_argument("--annotations", required=True, help="Path to manual rally annotations JSON.")
    parser.add_argument("--candidates", required=True, help="Path to rally candidates JSON.")
    parser.add_argument("--output", help="Optional path for the JSON evaluation report.")
    parser.add_argument(
        "--min-annotation-overlap",
        type=float,
        default=DEFAULT_MIN_ANNOTATION_OVERLAP,
        help="Minimum fraction of an annotated rally that a candidate must cover to count as a match.",
    )
    args = parser.parse_args(argv)

    report = evaluate_rallies(
        load_rally_annotations(args.annotations),
        load_candidates(args.candidates),
        min_annotation_overlap=args.min_annotation_overlap,
    )

    print(_format_summary(report))
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_intervals(data: Any, *, preferred_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object or array of intervals.")
    for key in preferred_keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    raise ValueError(f"Expected one of these interval arrays: {', '.join(preferred_keys)}")


def _normalize_interval(item: dict[str, Any], prefix: str, index: int) -> dict[str, Any]:
    start = _number(item, "startSec", "start_sec")
    end = _number(item, "endSec", "end_sec")
    if end <= start:
        raise ValueError(f"{prefix} interval must end after it starts: {item}")
    return {
        **item,
        "id": str(item.get("id") or f"{prefix}-{index:03d}"),
        "startSec": start,
        "endSec": end,
        "durationSec": end - start,
    }


def _number(item: dict[str, Any], *keys: str) -> float:
    for key in keys:
        if key in item:
            return float(item[key])
    raise ValueError(f"Missing required numeric field. Expected one of: {', '.join(keys)}")


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
        return 0
    return round(sum(values) / len(values), 3)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0
    return round(numerator / denominator, 4)


def _format_summary(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Rally evaluation",
            f"- rallies: {report['totalRallies']}",
            f"- candidates: {report['totalCandidates']}",
            f"- matchedRallies: {report['matchedRallies']}",
            f"- missedRallies: {report['missedRallies']}",
            f"- falsePositives: {report['falsePositives']}",
            f"- mergedCandidates: {report['mergedCandidates']}",
            f"- fragmentedRallies: {report['fragmentedRallies']}",
            f"- recall: {report['recall']:.4f}",
            f"- precision: {report['precision']:.4f}",
            f"- boundaryErrorSec.averageStart: {report['boundaryErrorSec']['averageStart']}",
            f"- boundaryErrorSec.averageEnd: {report['boundaryErrorSec']['averageEnd']}",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
