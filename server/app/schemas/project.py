from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.clip import ClipRead
from app.schemas.marker import MarkerRead
from app.schemas.video import SourceVideoRead


class ProjectCreate(BaseModel):
    name: str
    video_id: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    source_video: SourceVideoRead | None = None
    markers: list[MarkerRead] = []
    clips: list[ClipRead] = []
    created_at: datetime
    updated_at: datetime
