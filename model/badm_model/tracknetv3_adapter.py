from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from badm_model.contracts import ShuttlePoint, ShuttlePointsResult
from badm_model.io import ensure_dir, read_csv_rows
from badm_model.video_metadata import VideoMetadata


REQUIRED_COLUMNS = {"Frame", "Visibility", "X", "Y"}


@dataclass(frozen=True)
class TrackNetV3Config:
    tracknet_repo: Path
    tracknet_checkpoint: Path
    inpaintnet_checkpoint: Path | None = None
    python: str = "python"


@dataclass(frozen=True)
class TrackNetV3Run:
    csv_path: Path
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def convert_tracknet_csv(
    *,
    csv_path: Path,
    video_path: Path,
    metadata: VideoMetadata,
) -> ShuttlePointsResult:
    rows = read_csv_rows(csv_path)
    if not rows:
        raise ValueError(f"TrackNet CSV is empty: {csv_path}")

    missing = sorted(REQUIRED_COLUMNS - set(rows[0].keys()))
    if missing:
        raise ValueError(f"Missing required TrackNet CSV columns: {', '.join(missing)}")

    points: list[ShuttlePoint] = []
    for row in rows:
        frame_index = int(row["Frame"])
        visible = int(row["Visibility"]) == 1
        points.append(
            ShuttlePoint(
                frameIndex=frame_index,
                timeSec=round(frame_index / metadata.fps, 6),
                x=float(row["X"]),
                y=float(row["Y"]),
                confidence=1.0 if visible else 0.0,
                visible=visible,
            )
        )

    return ShuttlePointsResult(
        sourceVideo=str(video_path),
        source="tracknetv3",
        fps=metadata.fps,
        frameWidth=metadata.frame_width,
        frameHeight=metadata.frame_height,
        points=points,
    )


def run_tracknetv3_predict(
    *,
    video_path: Path,
    output_dir: Path,
    config: TrackNetV3Config,
    large_video: bool = False,
    eval_mode: str = "nonoverlap",
    skip_inpaintnet: bool = False,
    batch_size: int = 1,
) -> TrackNetV3Run:
    _validate_tracknet_inputs(video_path=video_path, config=config)

    raw_dir = ensure_dir(output_dir / "tracknet_raw")
    cmd = [
        config.python,
        "predict.py",
        "--video_file",
        _as_tracknet_video_arg(video_path),
        "--tracknet_file",
        str(config.tracknet_checkpoint),
        "--save_dir",
        str(raw_dir),
        "--eval_mode",
        eval_mode,
        "--batch_size",
        str(batch_size),
    ]
    if config.inpaintnet_checkpoint and not skip_inpaintnet:
        cmd.extend(["--inpaintnet_file", str(config.inpaintnet_checkpoint)])
    if large_video:
        cmd.append("--large_video")

    completed = subprocess.run(
        cmd,
        cwd=config.tracknet_repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    csv_path = raw_dir / f"{video_path.stem}_ball.csv"
    if completed.returncode != 0:
        return TrackNetV3Run(csv_path=csv_path, command=cmd, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
    if not csv_path.exists():
        return TrackNetV3Run(csv_path=csv_path, command=cmd, returncode=1, stdout=completed.stdout, stderr=f"TrackNetV3 did not create expected CSV: {csv_path}")
    return TrackNetV3Run(csv_path=csv_path, command=cmd, returncode=0, stdout=completed.stdout, stderr=completed.stderr)


def _validate_tracknet_inputs(*, video_path: Path, config: TrackNetV3Config) -> None:
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not (config.tracknet_repo / "predict.py").exists():
        raise FileNotFoundError(
            f"TrackNetV3 submodule is missing at {config.tracknet_repo}. "
            "Run: git submodule update --init --recursive"
        )
    if not config.tracknet_checkpoint.exists():
        raise FileNotFoundError(f"TrackNet checkpoint not found: {config.tracknet_checkpoint}")
    if config.inpaintnet_checkpoint and not config.inpaintnet_checkpoint.exists():
        raise FileNotFoundError(f"InpaintNet checkpoint not found: {config.inpaintnet_checkpoint}")


def _as_tracknet_video_arg(video_path: Path) -> str:
    return str(video_path).replace("\\", "/")


def run_to_metadata_dict(run: TrackNetV3Run) -> dict:
    return {
        **asdict(run),
        "csv_path": str(run.csv_path),
    }
