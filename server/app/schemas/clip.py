from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ClipExportStatus = Literal["none", "exporting", "completed", "failed"]


class ClipCreate(BaseModel):
    start_time_sec: float
    end_time_sec: float
    label: str = ""
    notes: str = ""
    anchor_marker_id: str | None = None


class ClipUpdate(BaseModel):
    start_time_sec: float | None = None
    end_time_sec: float | None = None
    label: str | None = None
    notes: str | None = None
    anchor_marker_id: str | None = None
    export_status: ClipExportStatus | None = None
    exported_file_path: str | None = None


class ClipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    start_time_sec: float
    end_time_sec: float
    label: str
    notes: str
    anchor_marker_id: str | None
    export_status: str
    exported_file_path: str | None
    created_at: datetime
