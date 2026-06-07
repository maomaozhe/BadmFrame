import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.evaluate_rallies import evaluate_rallies, load_candidates, load_rally_annotations
from app.schemas.rally import RallyCandidateRead
from app.services.rally_evaluation import RallyInterval, evaluate_candidates, load_annotations


def _annotations(*ranges):
    return [{"id": f"rally-{index:03d}", "startSec": start, "endSec": end} for index, (start, end) in enumerate(ranges, 1)]


def _candidates(*ranges):
    return [
        {
            "id": f"candidate-{index:03d}",
            "startSec": start,
            "endSec": end,
            "confidence": 0.8,
            "reason": ["test"],
        }
        for index, (start, end) in enumerate(ranges, 1)
    ]


def test_exact_matches_report_full_recall_and_precision():
    report = evaluate_rallies(_annotations((10, 20), (30, 40)), _candidates((10, 20), (30, 40)))

    assert report["matchedRallies"] == 2
    assert report["missedRallies"] == 0
    assert report["falsePositives"] == 0
    assert report["mergedCandidates"] == 0
    assert report["fragmentedRallies"] == 0
    assert report["recall"] == 1
    assert report["precision"] == 1
    assert report["boundaryErrorSec"]["averageStart"] == 0
    assert report["boundaryErrorSec"]["averageEnd"] == 0


def test_missed_rallies_are_reported_when_no_candidate_overlaps_enough():
    report = evaluate_rallies(_annotations((10, 20), (30, 40)), _candidates((10, 20)))

    assert report["matchedRallies"] == 1
    assert report["missedRallies"] == 1
    assert report["missedRallyIds"] == ["rally-002"]
    assert report["recall"] == 0.5


def test_false_positives_are_reported_for_unmatched_candidates():
    report = evaluate_rallies(_annotations((10, 20)), _candidates((10, 20), (50, 60)))

    assert report["matchedRallies"] == 1
    assert report["falsePositives"] == 1
    assert report["falsePositiveCandidateIds"] == ["candidate-002"]
    assert report["precision"] == 0.5


def test_boundary_offsets_are_averaged_for_best_matches():
    report = evaluate_rallies(_annotations((10, 20), (30, 40)), _candidates((8, 23), (31, 42)))

    assert report["matchedRallies"] == 2
    assert report["boundaryErrorSec"]["averageStart"] == 1.5
    assert report["boundaryErrorSec"]["averageEnd"] == 2.5


def test_one_candidate_covering_multiple_rallies_counts_as_merged_candidate():
    report = evaluate_rallies(_annotations((10, 20), (24, 30)), _candidates((9, 31)))

    assert report["matchedRallies"] == 2
    assert report["falsePositives"] == 0
    assert report["mergedCandidates"] == 1
    assert report["mergedCandidateIds"] == ["candidate-001"]


def test_multiple_candidates_covering_one_rally_counts_as_fragmented_rally():
    report = evaluate_rallies(_annotations((10, 30)), _candidates((10, 19), (19, 30)))

    assert report["matchedRallies"] == 1
    assert report["falsePositives"] == 0
    assert report["fragmentedRallies"] == 1
    assert report["fragmentedRallyIds"] == ["rally-001"]


def test_loads_repository_annotation_and_candidate_json_formats():
    annotations = load_rally_annotations(ROOT / "assets/reference/rally_annotations_140.json")
    candidates = load_candidates(ROOT / "server/tests/fixtures/rally_candidates.example.json")

    report = evaluate_rallies(annotations, candidates)

    assert len(annotations) == 16
    assert len(candidates) == 9
    assert report["totalRallies"] == 16
    assert report["totalCandidates"] == 9
    assert report["matchedRallies"] > 0


def test_cli_writes_json_report(tmp_path):
    from tools.evaluate_rallies import main

    output = tmp_path / "report.json"

    exit_code = main(
        [
            "--annotations",
            str(ROOT / "assets/reference/rally_annotations_140.json"),
            "--candidates",
            str(ROOT / "server/tests/fixtures/rally_candidates.example.json"),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["matchedRallies"] == 8
    assert report["falsePositives"] == 1


def test_service_reports_matches_boundary_errors_misses_and_false_rallies():
    annotations = [
        RallyInterval(id="rally-001", start_sec=10, end_sec=20),
        RallyInterval(id="rally-002", start_sec=30, end_sec=40),
    ]
    candidates = [
        RallyCandidateRead(
            id="candidate-001",
            start_sec=8,
            end_sec=23,
            confidence=0.9,
            review_state="pending",
            start_reason=[],
            end_reason=[],
            source="model",
        ),
        RallyCandidateRead(
            id="candidate-002",
            start_sec=50,
            end_sec=60,
            confidence=0.8,
            review_state="pending",
            start_reason=[],
            end_reason=[],
            source="model",
        ),
    ]

    report = evaluate_candidates(annotations, candidates, overlap_threshold=0.3)

    assert report.matched_rallies == 1
    assert report.missed_rallies == 1
    assert report.false_rallies == 1
    assert report.mean_start_error_sec == 2
    assert report.mean_end_error_sec == 3


def test_service_counts_one_candidate_covering_multiple_annotations_as_merged():
    annotations = [
        RallyInterval(id="rally-001", start_sec=10, end_sec=20),
        RallyInterval(id="rally-002", start_sec=24, end_sec=30),
    ]
    candidates = [
        RallyCandidateRead(
            id="candidate-001",
            start_sec=9,
            end_sec=31,
            confidence=0.9,
            review_state="pending",
            start_reason=[],
            end_reason=[],
            source="model",
        )
    ]

    report = evaluate_candidates(annotations, candidates, overlap_threshold=0.3)

    assert report.matched_rallies == 2
    assert report.false_rallies == 0
    assert report.merged_rallies == 1


def test_service_loads_reference_annotations():
    annotations = load_annotations(ROOT / "assets/reference/rally_annotations_140.json")

    assert len(annotations) == 8
    assert annotations[0].end_sec > annotations[0].start_sec
