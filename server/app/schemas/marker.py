from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

MarkerColor = Literal["yellow", "red", "blue", "green", "orange", "purple"]


class MarkerCreate(BaseModel):
    timestamp_sec: float
    label: str = ""
    color: MarkerColor = "yellow"


class MarkerUpdate(BaseModel):
    timestamp_sec: float | None = None
    label: str | None = None
    color: MarkerColor | None = None


class MarkerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp_sec: float
    label: str
    color: str
    created_at: datetime
