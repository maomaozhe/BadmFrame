from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.config import settings
from app.schemas.analysis import AnalysisSegment

_GPU_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rally-detection")


def create_rally_task_id() -> str:
    return str(uuid.uuid4())


def submit_rally_detection(
    *,
    task_id: str,
    video_id: str,
    project_id: str | None,
    video_path: Path,
) -> None:
    """Submit a GPU-heavy detection job to a single-worker queue."""
    _GPU_EXECUTOR.submit(
        _run_rally_detection_job,
        task_id=task_id,
        video_id=video_id,
        project_id=project_id,
        video_path=video_path,
    )


def _run_rally_detection_job(
    *,
    task_id: str,
    video_id: str,
    project_id: str | None,
    video_path: Path,
) -> None:
    save_rally_progress(
        task_id,
        {
            "stage": "running",
            "progress": 0.02,
            "message": "Starting full TrackNetV3 pipeline",
        },
    )
    try:
        run_rally_detection(
            task_id=task_id,
            video_id=video_id,
            project_id=project_id,
            video_path=video_path,
        )
    except Exception as error:
        result = {
            "task_id": task_id,
            "video_id": video_id,
            "project_id": project_id,
            "status": "failed",
            "progress": 1.0,
            "duration_sec": 0,
            "segments": [],
            "candidate_count": 0,
            "error": str(error),
        }
        _save_task(task_id, result)
        save_rally_progress(
            task_id,
            {
                "stage": "failed",
                "progress": 1.0,
                "message": str(error),
            },
        )


def run_rally_detection(
    *,
    task_id: str,
    video_id: str,
    project_id: str | None,
    video_path: Path,
) -> dict[str, Any]:
    """Run the full rally-detection pipeline and return structured results.

    Spawns ``model/scripts/run_pipeline.py`` as a subprocess (which in turn
    runs TrackNetV3 as its own subprocess).  MVP runs synchronously — Celery
    integration is provided in ``app/tasks/rally_detection.py``.
    """
    output_dir = _rallies_dir() / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline_script = _resolve_pipeline_script()
    progress_file = output_dir / "progress.json"
    config_path = _resolve_tracknet_config()
    model_python = _resolve_model_python(config_path)

    # Resolve paths to absolute so they work regardless of subprocess cwd.
    abs_video_path = str(video_path.resolve())
    abs_output_dir = str(output_dir.resolve())

    cmd = [
        model_python,
        str(pipeline_script),
        "--video", abs_video_path,
        "--config", str(config_path),
        "--output-dir", abs_output_dir,
        "--progress-file", str(progress_file),
        "--large-video",
        "--batch-size", str(settings.tracknet_batch_size),
        "--eval-mode", settings.tracknet_eval_mode,
    ]
    if settings.tracknet_skip_inpaintnet:
        cmd.append("--skip-inpaintnet")

    env = os.environ.copy()
    if settings.tracknet_cuda_alloc_conf:
        env["PYTORCH_CUDA_ALLOC_CONF"] = settings.tracknet_cuda_alloc_conf
    env.setdefault("CUDA_MODULE_LOADING", "LAZY")

    completed = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=3600,  # 1 hour — TrackNetV3 inference is slow
    )

    if completed.returncode != 0:
        result = {
            "task_id": task_id,
            "video_id": video_id,
            "project_id": project_id,
            "status": "failed",
            "progress": 1.0,
            "duration_sec": 0,
            "segments": [],
            "error": completed.stderr.strip() or completed.stdout.strip() or "Pipeline failed",
        }
        _save_task(task_id, result)
        return result

    candidates_path = output_dir / "rally_candidates.json"
    if not candidates_path.exists():
        result = {
            "task_id": task_id,
            "video_id": video_id,
            "project_id": project_id,
            "status": "failed",
            "progress": 1.0,
            "duration_sec": 0,
            "segments": [],
            "error": f"Pipeline completed but rally_candidates.json not found at {candidates_path}",
        }
        _save_task(task_id, result)
        return result

    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidates: list[dict] = data.get("candidates", [])
    duration_sec = float(data.get("durationSec", 0))

    keep_segments = [
        AnalysisSegment(
            start_sec=float(c["startSec"]),
            end_sec=float(c["endSec"]),
            confidence=float(c.get("confidence", 0.8)),
            reason=c.get("startReason", []) + c.get("endReason", []),
            state="keep",
        )
        for c in candidates
    ]

    timeline = _with_cut_segments(keep_segments, duration_sec)

    result = {
        "task_id": task_id,
        "video_id": video_id,
        "project_id": project_id,
        "status": "completed",
        "progress": 1.0,
        "duration_sec": duration_sec,
        "segments": [s.model_dump() for s in timeline],
        "candidate_count": len(candidates),
        "error": None,
    }
    _save_task(task_id, result)
    return result


def load_rally_result(task_id: str) -> dict[str, Any] | None:
    path = _rallies_dir() / f"{task_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_rally_progress(task_id: str) -> dict[str, Any] | None:
    path = _rallies_dir() / task_id / "progress.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_rally_progress(task_id: str, progress: dict[str, Any]) -> None:
    path = _rallies_dir() / task_id / "progress.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


# ── helpers ───────────────────────────────────────────────────────────


def _resolve_tracknet_config() -> Path:
    """Resolve model/configs/tracknetv3.local.json."""
    server_services_dir = Path(__file__).resolve().parent
    project_root = server_services_dir.parents[2]
    config = project_root / "model" / "configs" / "tracknetv3.local.json"
    if not config.exists():
        raise FileNotFoundError(
            f"TrackNetV3 config not found at {config}. "
            "Copy model/configs/tracknetv3.local.example.json and edit paths."
        )
    return config


def _resolve_model_python(config_path: Path) -> str:
    """Read the python executable path from the TrackNetV3 config.

    Uses the same Python that has PyTorch / CUDA available (model/.local/venv).
    Falls back to ``sys.executable`` if the config has no explicit ``python`` key.
    """
    data = json.loads(config_path.read_text(encoding="utf-8"))
    python = data.get("python")
    if python and Path(python).exists():
        return python
    if not python:
        return sys.executable
    raise FileNotFoundError(
        f"Model Python not found at {python}. "
        "Check the 'python' field in model/configs/tracknetv3.local.json."
    )


def _resolve_pipeline_script() -> Path:
    """Resolve model/scripts/run_pipeline.py relative to the project root.

    The server package lives at ``server/app/services/``, so the project root
    is three levels up.
    """
    server_services_dir = Path(__file__).resolve().parent  # .../server/app/services
    project_root = server_services_dir.parents[2]  # worktree root
    script = project_root / "model" / "scripts" / "run_pipeline.py"
    if not script.exists():
        raise FileNotFoundError(
            f"Pipeline script not found at {script}. "
            "Ensure model/scripts/run_pipeline.py exists."
        )
    return script


def _rallies_dir() -> Path:
    return settings.storage_dir / "rallies"


def _save_task(task_id: str, result: dict[str, Any]) -> None:
    _rallies_dir().mkdir(parents=True, exist_ok=True)
    path = _rallies_dir() / f"{task_id}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def _with_cut_segments(
    keep_segments: list[AnalysisSegment],
    duration_sec: float,
) -> list[AnalysisSegment]:
    """Fill gaps between keep segments with cut segments (same pattern as analysis.py)."""
    timeline: list[AnalysisSegment] = []
    cursor = 0.0
    for keep in sorted(keep_segments, key=lambda s: s.start_sec):
        if keep.start_sec > cursor:
            timeline.append(
                AnalysisSegment(
                    start_sec=round(cursor, 3),
                    end_sec=round(keep.start_sec, 3),
                    confidence=0.7,
                    reason=["low_activity"],
                    state="cut",
                )
            )
        timeline.append(keep)
        cursor = max(cursor, keep.end_sec)
    if cursor < duration_sec:
        timeline.append(
            AnalysisSegment(
                start_sec=round(cursor, 3),
                end_sec=round(duration_sec, 3),
                confidence=0.7,
                reason=["low_activity"],
                state="cut",
            )
        )
    return [s for s in timeline if s.end_sec > s.start_sec]
