from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceVideoBase(BaseModel):
    file_name: str = ""
    file_path: str = ""
    duration_sec: float = 0
    width: int = 0
    height: int = 0
    frame_rate: float = 0
    codec: str = ""
    is_vfr: bool = False
    file_size: int = 0


class SourceVideoRead(SourceVideoBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str | None = None
    import_date: datetime
