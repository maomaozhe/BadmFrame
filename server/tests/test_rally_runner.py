import json
from pathlib import Path

import pytest

from app.services.rally_runner import run_rally_detection


def test_runner_imports_candidates_from_configured_json(tmp_path, monkeypatch):
    candidates_path = tmp_path / "rally_candidates.json"
    candidates_path.write_text(
        json.dumps(
            {
                "video": "sample.mp4",
                "source": "imported-json",
                "candidates": [
                    {"id": "rally-002", "startSec": 30, "endSec": 40, "confidence": 0.7},
                    {"id": "rally-001", "startSec": 10, "endSec": 20, "confidence": 0.8},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("BADMFRAME_RALLY_CANDIDATES_PATH", str(candidates_path))

    candidates = run_rally_detection(Path("sample.mp4"), duration_sec=80)

    assert [candidate.id for candidate in candidates] == ["rally-001", "rally-002"]
    assert candidates[0].source == "imported-json"


def test_runner_fails_clearly_when_no_source_is_configured(monkeypatch):
    monkeypatch.delenv("BADMFRAME_RALLY_CANDIDATES_PATH", raising=False)

    with pytest.raises(RuntimeError, match="Rally detection runner is not configured"):
        run_rally_detection(Path("sample.mp4"), duration_sec=80)
