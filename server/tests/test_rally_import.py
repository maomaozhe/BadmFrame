import json

import pytest
from pydantic import ValidationError

from app.services.rally_import import load_rally_candidates, parse_rally_candidates_payload


def test_parse_rally_candidates_payload_normalizes_camel_case_fields():
    candidates = parse_rally_candidates_payload(
        {
            "video": "sample.mp4",
            "source": "imported-json",
            "candidates": [
                {
                    "id": "rally-001",
                    "startSec": 14,
                    "endSec": 21,
                    "confidence": 0.8,
                    "startReason": ["manual_seed"],
                    "endReason": ["manual_seed"],
                }
            ],
        }
    )

    assert len(candidates) == 1
    assert candidates[0].id == "rally-001"
    assert candidates[0].start_sec == 14
    assert candidates[0].end_sec == 21
    assert candidates[0].review_state == "pending"
    assert candidates[0].source == "imported-json"
    assert candidates[0].start_reason == ["manual_seed"]
    assert candidates[0].end_reason == ["manual_seed"]


def test_load_rally_candidates_sorts_by_start_time(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(
        json.dumps(
            {
                "video": "sample.mp4",
                "candidates": [
                    {"id": "rally-002", "startSec": 30, "endSec": 40, "confidence": 0.7},
                    {"id": "rally-001", "startSec": 10, "endSec": 20, "confidence": 0.8},
                ],
            }
        ),
        encoding="utf-8",
    )

    candidates = load_rally_candidates(path)

    assert [candidate.id for candidate in candidates] == ["rally-001", "rally-002"]


def test_parse_rally_candidates_payload_rejects_invalid_time_range():
    with pytest.raises(ValidationError):
        parse_rally_candidates_payload(
            {
                "video": "sample.mp4",
                "candidates": [
                    {"id": "rally-001", "startSec": 20, "endSec": 20, "confidence": 0.8},
                ],
            }
        )
