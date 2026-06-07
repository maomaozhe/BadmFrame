from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ShuttlePoint:
    frameIndex: int
    timeSec: float
    x: float
    y: float
    confidence: float
    visible: bool
    source: str = "tracknetv3"


@dataclass(frozen=True)
class ShuttlePointsResult:
    sourceVideo: str
    source: str
    fps: float
    frameWidth: int
    frameHeight: int
    points: list[ShuttlePoint]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sourceVideo": self.sourceVideo,
            "source": self.source,
            "fps": self.fps,
            "frameWidth": self.frameWidth,
            "frameHeight": self.frameHeight,
            "points": [asdict(point) for point in self.points],
        }

