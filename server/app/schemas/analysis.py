from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AnalysisMode = Literal["conservative", "balanced", "aggressive"]
AnalysisStatus = Literal["queued", "running", "completed", "failed"]
SegmentState = Literal["keep", "cut"]


class AnalysisParams(BaseModel):
    mode: AnalysisMode = "balanced"
    pre_buffer_sec: float | None = Field(default=None, ge=0)
    post_buffer_sec: float | None = Field(default=None, ge=0)


class AnalysisSegment(BaseModel):
    start_sec: float
    end_sec: float
    confidence: float = Field(ge=0, le=1)
    reason: list[str] = []
    source: Literal["auto"] = "auto"
    state: SegmentState


class AnalysisStartResponse(BaseModel):
    task_id: str
    status: AnalysisStatus


class AnalysisResultRead(BaseModel):
    task_id: str
    video_id: str
    project_id: str | None = None
    status: AnalysisStatus
    params: AnalysisParams
    progress: float = Field(ge=0, le=1)
    duration_sec: float = 0
    segments: list[AnalysisSegment] = []
    error: str | None = None


class AutoClipsApplyRequest(BaseModel):
    task_id: str
    replace_existing_auto: bool = False


class AutoClipsApplyResponse(BaseModel):
    created_clip_ids: list[str]
    clips_created: int


class AnalysisJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    video_id: str
    project_id: str | None
    status: AnalysisStatus
    params: AnalysisParams
    progress: float = Field(ge=0, le=1)
    duration_sec: float = 0
    keep_segments: int = 0
    cut_segments: int = 0
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
