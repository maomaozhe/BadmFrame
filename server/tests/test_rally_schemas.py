import pytest
from pydantic import ValidationError

from app.schemas.rally import RallyCandidateRead, RallyCandidatesApplyRequest


def test_pending_candidate_schema_accepts_minimum_contract():
    candidate = RallyCandidateRead(
        id="rally-001",
        start_sec=14,
        end_sec=21,
        confidence=0.82,
        review_state="pending",
        start_reason=["trajectory_active"],
        end_reason=["trajectory_missing"],
        source="imported-json",
    )

    assert candidate.id == "rally-001"
    assert candidate.review_state == "pending"
    assert candidate.source == "imported-json"


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_candidate_confidence_must_be_between_zero_and_one(confidence):
    with pytest.raises(ValidationError):
        RallyCandidateRead(
            id="rally-001",
            start_sec=14,
            end_sec=21,
            confidence=confidence,
            review_state="pending",
            start_reason=[],
            end_reason=[],
            source="model",
        )


@pytest.mark.parametrize(("start_sec", "end_sec"), [(10, 10), (12, 10)])
def test_candidate_end_must_be_after_start(start_sec, end_sec):
    with pytest.raises(ValidationError):
        RallyCandidateRead(
            id="rally-001",
            start_sec=start_sec,
            end_sec=end_sec,
            confidence=0.8,
            review_state="pending",
            start_reason=[],
            end_reason=[],
            source="model",
        )


def test_apply_request_defaults_exclude_pending_candidates():
    request = RallyCandidatesApplyRequest(task_id="task-001")

    assert request.include_pending is False
    assert request.replace_existing_rally is False
