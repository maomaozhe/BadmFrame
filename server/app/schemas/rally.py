from typing import Literal

from pydantic import BaseModel, Field, model_validator

RallyReviewState = Literal["pending", "accepted", "rejected", "adjusted"]
RallySource = Literal["model", "imported-json", "manual"]
RallyAnalysisStatus = Literal["queued", "running", "completed", "failed"]


class TrajectoryStats(BaseModel):
    visible_ratio: float | None = Field(default=None, ge=0, le=1)
    max_gap_sec: float | None = Field(default=None, ge=0)
    direction_changes: int | None = Field(default=None, ge=0)
    mean_speed_px_sec: float | None = Field(default=None, ge=0)


class RallyCandidateRead(BaseModel):
    id: str
    start_sec: float = Field(ge=0)
    end_sec: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    review_state: RallyReviewState = "pending"
    start_reason: list[str] = Field(default_factory=list)
    end_reason: list[str] = Field(default_factory=list)
    source: RallySource
    trajectory_stats: TrajectoryStats | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "RallyCandidateRead":
        if self.end_sec <= self.start_sec:
            raise ValueError("end_sec must be greater than start_sec")
        return self


class RallyAnalysisResultRead(BaseModel):
    task_id: str
    video_id: str
    project_id: str | None = None
    status: RallyAnalysisStatus
    progress: float = Field(ge=0, le=1)
    duration_sec: float = Field(default=0, ge=0)
    candidates: list[RallyCandidateRead] = Field(default_factory=list)
    error: str | None = None


class RallyCandidateUpdate(BaseModel):
    id: str
    start_sec: float | None = Field(default=None, ge=0)
    end_sec: float | None = Field(default=None, ge=0)
    review_state: RallyReviewState | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "RallyCandidateUpdate":
        if self.start_sec is not None and self.end_sec is not None and self.end_sec <= self.start_sec:
            raise ValueError("end_sec must be greater than start_sec")
        return self


class RallyCandidatesApplyRequest(BaseModel):
    task_id: str
    include_pending: bool = False
    replace_existing_rally: bool = False
    candidates: list[RallyCandidateUpdate] | None = None


class RallyCandidatesApplyResponse(BaseModel):
    created_clip_ids: list[str] = Field(default_factory=list)
    clips_created: int
