from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ExportMode = Literal["separate", "merged"]
ExportPreset = Literal["auto", "fast_copy", "compatible"]
ExportStatus = Literal["queued", "running", "completed", "failed"]


class ExportRequest(BaseModel):
    project_id: str
    clip_ids: list[str]
    mode: ExportMode = "separate"
    preset: ExportPreset = "auto"
    merge: bool = False


class ExportTaskRead(BaseModel):
    task_id: str
    status: ExportStatus
    mode: ExportMode = "separate"
    preset: ExportPreset = "auto"
    results: list[dict] = []
    error: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class ExportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    project_id: str
    status: ExportStatus
    mode: ExportMode
    preset: ExportPreset
    results: list[dict] = []
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
