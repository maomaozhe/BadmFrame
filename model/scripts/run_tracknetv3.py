from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "model"))

from badm_model.io import ensure_dir, write_json
from badm_model.tracknetv3_adapter import TrackNetV3Config, convert_tracknet_csv, run_tracknetv3_predict
from badm_model.video_metadata import VideoMetadata, read_video_metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run TrackNetV3 and write BadmFrame shuttle_points.json.")
    parser.add_argument("--video", required=True, help="Source video path.")
    parser.add_argument("--config", help="Local TrackNetV3 JSON config.")
    parser.add_argument("--output-dir", required=True, help="Run output directory.")
    parser.add_argument("--large-video", action="store_true", help="Pass --large_video to TrackNetV3.")
    parser.add_argument("--skip-predict", action="store_true", help="Skip TrackNetV3 and convert an existing CSV.")
    parser.add_argument("--tracknet-csv", help="Existing TrackNet CSV for --skip-predict.")
    parser.add_argument("--fps", type=float, help="Override fps, intended for dry tests.")
    parser.add_argument("--frame-width", type=int, help="Override frame width, intended for dry tests.")
    parser.add_argument("--frame-height", type=int, help="Override frame height, intended for dry tests.")
    args = parser.parse_args(argv)

    started_at = time.time()
    video_path = Path(args.video)
    output_dir = ensure_dir(Path(args.output_dir))
    metadata_path = output_dir / "run_metadata.json"

    try:
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        video_metadata = _metadata_from_args(args) or read_video_metadata(video_path)

        if args.skip_predict:
            if not args.tracknet_csv:
                raise ValueError("--tracknet-csv is required with --skip-predict")
            csv_path = Path(args.tracknet_csv)
            command: list[str] = []
            stdout = ""
            stderr = ""
        else:
            config = _load_config(Path(args.config) if args.config else None)
            run = run_tracknetv3_predict(
                video_path=video_path,
                output_dir=output_dir,
                config=config,
                large_video=args.large_video,
            )
            csv_path = run.csv_path
            command = run.command
            stdout = run.stdout
            stderr = run.stderr
            if run.returncode != 0:
                _write_metadata(
                    metadata_path,
                    status="failed",
                    started_at=started_at,
                    args=args,
                    command=command,
                    stdout=stdout,
                    stderr=stderr,
                    csv_path=csv_path,
                )
                return run.returncode

        result = convert_tracknet_csv(csv_path=csv_path, video_path=video_path, metadata=video_metadata)
        write_json(output_dir / "shuttle_points.json", result)
        _write_metadata(
            metadata_path,
            status="completed",
            started_at=started_at,
            args=args,
            command=command,
            stdout=stdout,
            stderr=stderr,
            csv_path=csv_path,
            point_count=len(result.points),
        )
        return 0
    except Exception as error:
        _write_metadata(metadata_path, status="failed", started_at=started_at, args=args, error=str(error))
        print(str(error), file=sys.stderr)
        return 1


def _metadata_from_args(args: argparse.Namespace) -> VideoMetadata | None:
    if args.fps is None and args.frame_width is None and args.frame_height is None:
        return None
    if args.fps is None or args.frame_width is None or args.frame_height is None:
        raise ValueError("--fps, --frame-width, and --frame-height must be provided together")
    return VideoMetadata(fps=args.fps, frame_width=args.frame_width, frame_height=args.frame_height)


def _load_config(path: Path | None) -> TrackNetV3Config:
    if path is None:
        raise ValueError("--config is required unless --skip-predict is used")
    data = json.loads(path.read_text(encoding="utf-8"))
    return TrackNetV3Config(
        tracknet_repo=Path(data["tracknet_repo"]),
        tracknet_checkpoint=Path(data["tracknet_checkpoint"]),
        inpaintnet_checkpoint=Path(data["inpaintnet_checkpoint"]) if data.get("inpaintnet_checkpoint") else None,
        python=data.get("python", "python"),
    )


def _write_metadata(path: Path, *, status: str, started_at: float, args: argparse.Namespace, **extra) -> None:
    payload = {
        "status": status,
        "durationSec": round(time.time() - started_at, 3),
        "sourceVideo": args.video,
        "outputDir": args.output_dir,
        "skipPredict": bool(args.skip_predict),
        "largeVideo": bool(args.large_video),
        **{key: _stringify_paths(value) for key, value in extra.items()},
    }
    write_json(path, payload)


def _stringify_paths(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [str(item) if isinstance(item, Path) else item for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
