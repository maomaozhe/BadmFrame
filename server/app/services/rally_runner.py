from __future__ import annotations

import os
from pathlib import Path

from app.schemas.rally import RallyCandidateRead
from app.services.rally_import import load_rally_candidates


def run_rally_detection(video_path: Path, duration_sec: float) -> list[RallyCandidateRead]:
    candidates_path = os.environ.get("BADMFRAME_RALLY_CANDIDATES_PATH")
    if candidates_path:
        return load_rally_candidates(Path(candidates_path))
    raise RuntimeError("Rally detection runner is not configured")
