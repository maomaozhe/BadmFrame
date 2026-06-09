from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "model"))

from typing import Sequence

from badm_model.contracts import ShuttlePoint
from badm_model.io import ensure_dir, write_json
from badm_model.rally_refiner import RallyRefinerConfig, refine_candidates
from badm_model.rally_state_machine import RallyCandidate
from badm_model.rally_tuner import WindowSegmentationConfig, _extract_windows, _generate_candidates_from_windows
from badm_model.tracknetv3_adapter import TrackNetV3Config, convert_tracknet_csv, run_tracknetv3_predict
from badm_model.trajectory_cleaner import clean_trajectory
from badm_model.video_metadata import VideoMetadata, read_video_metadata

DEFAULT_PARAMS_PATH = Path(__file__).resolve().parent / "best_params.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Full rally-detection pipeline: video → rally_candidates.json"
    )
    parser.add_argument("--video", required=True, help="Source video path.")
    parser.add_argument("--config", help="TrackNetV3 JSON config (required unless --skip-tracknet).")
    parser.add_argument("--output-dir", required=True, help="Run output directory.")
    parser.add_argument("--best-params", help="JSON with window + refiner parameters.")
    parser.add_argument("--skip-tracknet", action="store_true", help="Skip inference, use existing CSV.")
    parser.add_argument("--tracknet-csv", help="Existing TrackNet CSV for --skip-tracknet.")
    parser.add_argument("--large-video", action="store_true", help="Pass --large_video to TrackNetV3.")
    parser.add_argument("--batch-size", type=int, default=1, help="TrackNetV3 inference batch size.")
    parser.add_argument("--eval-mode", default="nonoverlap", choices=["nonoverlap", "average", "weight"])
    parser.add_argument("--skip-inpaintnet", action="store_true", help="Do not load InpaintNet during inference.")
    parser.add_argument("--max-sample-num", type=int, default=400, help="Max frames for median image generation (lower = less memory).")
    parser.add_argument("--progress-file", help="Write progress updates to this JSON file.")
    parser.add_argument("--fps", type=float, help="Override fps (for dry tests).")
    parser.add_argument("--frame-width", type=int, help="Override frame width (for dry tests).")
    parser.add_argument("--frame-height", type=int, help="Override frame height (for dry tests).")
    args = parser.parse_args(argv)

    started_at = time.time()
    video_path = Path(args.video)
    output_dir = ensure_dir(Path(args.output_dir))

    try:
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        # Load best params (window + refiner config)
        params = _load_best_params(args.best_params)

        video_metadata = _metadata_from_args(args) or read_video_metadata(video_path)

        # ── Stage 1: TrackNetV3 inference ──────────────────────────
        _report(args.progress_file, "tracknet", 0.0, "Starting TrackNetV3 inference...")

        if args.skip_tracknet:
            if not args.tracknet_csv:
                raise ValueError("--tracknet-csv is required with --skip-tracknet")
            csv_path = Path(args.tracknet_csv)
        else:
            config = _load_config(Path(args.config) if args.config else None)
            run = run_tracknetv3_predict(
                video_path=video_path,
                output_dir=output_dir,
                config=config,
                large_video=args.large_video,
                batch_size=args.batch_size,
                eval_mode=args.eval_mode,
                skip_inpaintnet=args.skip_inpaintnet,
                max_sample_num=args.max_sample_num,
            )
            csv_path = run.csv_path
            if run.returncode != 0:
                _report(args.progress_file, "failed", 1.0, run.stderr)
                _write_metadata(output_dir / "run_metadata.json", "failed", started_at, args, error=run.stderr)
                return run.returncode

        _report(args.progress_file, "tracknet", 0.70, "TrackNetV3 inference complete.")

        # ── Stage 2: CSV → shuttle_points.json ─────────────────────
        _report(args.progress_file, "converting", 0.70, "Converting CSV to shuttle points...")

        result = convert_tracknet_csv(csv_path=csv_path, video_path=video_path, metadata=video_metadata)
        write_json(output_dir / "shuttle_points.json", result)
        fps = result.fps

        _report(args.progress_file, "converting", 0.75, f"Converted {len(result.points)} shuttle points.")

        # ── Stage 3: Trajectory cleaning ───────────────────────────
        _report(args.progress_file, "cleaning", 0.75, "Cleaning trajectory...")

        cleaned = clean_trajectory(
            result.points,
            frame_width=video_metadata.frame_width,
            frame_height=video_metadata.frame_height,
        )

        _report(args.progress_file, "cleaning", 0.78, f"Cleaned trajectory ({cleaned.removedCount} outliers removed).")

        # ── Stage 4: Window-based rally segmentation ───────────────
        _report(args.progress_file, "segmenting", 0.78, "Detecting rallies...")

        window_config = WindowSegmentationConfig(**params["window"]) if params.get("window") else WindowSegmentationConfig()
        windows = _extract_windows(cleaned.points, window_config)
        candidates = _generate_candidates_from_windows(windows, window_config)

        _report(args.progress_file, "segmenting", 0.85, f"Found {len(candidates)} rally candidates.")

        # ── Stage 5: Boundary refinement (optional) ────────────────
        if params.get("refiner"):
            _report(args.progress_file, "refining", 0.85, "Refining boundaries...")
            refiner_config = RallyRefinerConfig(**params["refiner"])
            candidates = refine_candidates(cleaned.points, candidates, refiner_config)
            _report(args.progress_file, "refining", 0.90, f"Refined to {len(candidates)} candidates.")

        # ── Stage 6: Write output ──────────────────────────────────
        _report(args.progress_file, "writing", 0.90, "Writing rally_candidates.json...")

        # Compute real trajectory stats from cleaned shuttle points for each candidate
        points = cleaned.points

        def _compute_stats_for(candidate) -> dict:
            seg_pts = [p for p in points if candidate.startSec <= p.timeSec <= candidate.endSec]
            return _compute_trajectory_stats(seg_pts)

        rally_output = {
            "source": "tracknetv3+pipeline",
            "sourceVideo": str(video_path),
            "fps": fps,
            "durationSec": round(result.points[-1].timeSec, 3) if result.points else 0,
            "params": params,
            "candidates": [
                {
                    "id": c.id,
                    "startSec": c.startSec,
                    "endSec": c.endSec,
                    "confidence": round(c.confidence, 4),
                    "startReason": c.startReason,
                    "endReason": c.endReason,
                    "reviewState": c.reviewState,
                    "trajectoryStats": _compute_stats_for(c),
                }
                for c in candidates
            ],
        }
        write_json(output_dir / "rally_candidates.json", rally_output)

        _write_metadata(
            output_dir / "run_metadata.json",
            "completed",
            started_at,
            args,
            candidate_count=len(candidates),
            point_count=len(result.points),
        )
        _report(args.progress_file, "completed", 1.0, f"Done. {len(candidates)} rally candidates.")
        return 0

    except Exception as error:
        _report(args.progress_file, "failed", 1.0, str(error))
        _write_metadata(output_dir / "run_metadata.json", "failed", started_at, args, error=str(error))
        print(str(error), file=sys.stderr)
        return 1


# ── trajectory stats ─────────────────────────────────────────────────


def _compute_trajectory_stats(points: Sequence[ShuttlePoint]) -> dict:
    """Compute real trajectory statistics for a candidate interval."""
    visible_pts = [p for p in points if p.visible]
    total = len(points)
    if total == 0:
        return {"visibleRatio": 0.0, "maxGapSec": 0.0, "directionChanges": 0, "meanSpeedPxSec": 0.0}

    visible_ratio = round(len(visible_pts) / total, 4)
    max_gap_sec = round(_longest_gap_sec(points), 4)
    dir_changes = _count_direction_changes(visible_pts)
    mean_speed = round(_mean_speed_px_sec(visible_pts), 1)
    return {
        "visibleRatio": visible_ratio,
        "maxGapSec": max_gap_sec,
        "directionChanges": dir_changes,
        "meanSpeedPxSec": mean_speed,
    }


def _longest_gap_sec(points: Sequence[ShuttlePoint]) -> float:
    max_gap = 0.0
    gap_start: float | None = None
    for p in points:
        if not p.visible:
            if gap_start is None:
                gap_start = p.timeSec
        else:
            if gap_start is not None:
                max_gap = max(max_gap, p.timeSec - gap_start)
                gap_start = None
    return max_gap


def _count_direction_changes(visible_points: Sequence[ShuttlePoint]) -> int:
    changes = 0
    for i in range(1, len(visible_points) - 1):
        dx1 = visible_points[i].x - visible_points[i - 1].x
        dy1 = visible_points[i].y - visible_points[i - 1].y
        dx2 = visible_points[i + 1].x - visible_points[i].x
        dy2 = visible_points[i + 1].y - visible_points[i].y
        if dx1 * dx2 + dy1 * dy2 < 0:
            changes += 1
    return changes


def _mean_speed_px_sec(visible_points: Sequence[ShuttlePoint]) -> float:
    if len(visible_points) < 2:
        return 0.0
    speeds: list[float] = []
    for i in range(1, len(visible_points)):
        dx = visible_points[i].x - visible_points[i - 1].x
        dy = visible_points[i].y - visible_points[i - 1].y
        dt = visible_points[i].timeSec - visible_points[i - 1].timeSec
        if dt > 0:
            speeds.append((dx**2 + dy**2) ** 0.5 / dt)
    return sum(speeds) / len(speeds) if speeds else 0.0


def _tighten_by_visibility(
    points: Sequence[ShuttlePoint],
    candidates: list,
    fps: float,
) -> list:
    """Tighten candidate boundaries to the first/last visible shuttle point.

    For each candidate, scan from the boundary regions to find where the
    shuttle trajectory has a meaningful gap or becomes invisible. This
    trims dead air at the edges that the window detector included.

    Uses a 2-pass approach: first looks for the last/first visible point in
    the boundary region, then falls back to looking for a significant gap
    (>0.5s) of invisible points near the edges.
    """
    START_GRACE_SEC = 0.5  # Buffer before first visible point
    END_GRACE_SEC = 0.8    # Buffer after last visible point (generous to preserve recall)
    MIN_TIGHTEN_SEC = 0.4   # Minimum change to apply tightening
    BOUNDARY_FRAC = 0.3     # Fraction of candidate to search for boundaries

    if not points:
        return candidates

    tightened = []
    for c in candidates:
        seg_pts = [p for p in points if c.startSec <= p.timeSec <= c.endSec]
        if len(seg_pts) < 3:
            tightened.append(c)
            continue

        dur = c.endSec - c.startSec
        boundary_sec = dur * BOUNDARY_FRAC

        # Find first visible point within the start boundary region
        start_region = [p for p in seg_pts if p.timeSec <= c.startSec + boundary_sec]
        first_vis = next((p for p in start_region if p.visible), None)

        # Find last visible point within the end boundary region
        end_region = [p for p in seg_pts if p.timeSec >= c.endSec - boundary_sec]
        last_vis = next((p for p in reversed(end_region) if p.visible), None)

        new_start = c.startSec
        new_end = c.endSec
        start_reason = list(c.startReason)
        end_reason = list(c.endReason)
        changed = False

        # Tighten start: move forward to first visible point minus small buffer
        if first_vis is not None and first_vis.timeSec > c.startSec + MIN_TIGHTEN_SEC:
            new_start = round(first_vis.timeSec - START_GRACE_SEC, 3)
            if new_start < c.startSec:
                new_start = c.startSec
            if new_start > c.startSec + MIN_TIGHTEN_SEC:
                changed = True
                start_reason.append("visibility_tightened_start")

        # Tighten end: move backward to last visible point plus small buffer
        if last_vis is not None and last_vis.timeSec < c.endSec - MIN_TIGHTEN_SEC:
            new_end = round(last_vis.timeSec + END_GRACE_SEC, 3)
            if new_end > c.endSec:
                new_end = c.endSec
            if new_end < c.endSec - MIN_TIGHTEN_SEC:
                changed = True
                end_reason.append("visibility_tightened_end")

        # Fallback: look for significant invisible gap near edges
        if not changed:
            # Near start: find first invisible gap >= 0.5s
            gap_start = None
            for p in start_region:
                if not p.visible:
                    if gap_start is None:
                        gap_start = p.timeSec
                else:
                    if gap_start is not None and p.timeSec - gap_start >= 0.5:
                        new_start = round(gap_start + 0.5, 3)
                        if new_start > c.startSec + MIN_TIGHTEN_SEC:
                            changed = True
                            start_reason.append("gap_tightened_start")
                        break
                    gap_start = None

        if not changed or new_start >= new_end:
            tightened.append(c)
            continue

        tightened.append(
            RallyCandidate(
                id=c.id,
                startSec=new_start,
                endSec=new_end,
                confidence=c.confidence,
                startReason=start_reason,
                endReason=end_reason,
                reviewState=c.reviewState,
                trajectoryStats=c.trajectoryStats,
            )
        )
    return tightened


# ── helpers ───────────────────────────────────────────────────────────


def _report(path_str: str | None, stage: str, progress: float, message: str) -> None:
    if not path_str:
        return
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"stage": stage, "progress": round(progress, 4), "message": message}, ensure_ascii=False),
        encoding="utf-8",
    )


def _load_best_params(path_str: str | None) -> dict:
    if path_str:
        path = Path(path_str)
    else:
        path = DEFAULT_PARAMS_PATH
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _load_config(path: Path | None) -> TrackNetV3Config:
    if path is None:
        raise ValueError("--config is required unless --skip-tracknet is used")
    data = json.loads(path.read_text(encoding="utf-8"))
    return TrackNetV3Config(
        tracknet_repo=Path(data["tracknet_repo"]),
        tracknet_checkpoint=Path(data["tracknet_checkpoint"]),
        inpaintnet_checkpoint=Path(data["inpaintnet_checkpoint"]) if data.get("inpaintnet_checkpoint") else None,
        python=data.get("python", "python"),
    )


def _metadata_from_args(args: argparse.Namespace) -> VideoMetadata | None:
    if args.fps is None and args.frame_width is None and args.frame_height is None:
        return None
    if args.fps is None or args.frame_width is None or args.frame_height is None:
        raise ValueError("--fps, --frame-width, and --frame-height must be provided together")
    return VideoMetadata(fps=args.fps, frame_width=args.frame_width, frame_height=args.frame_height)


def _write_metadata(path: Path, status: str, started_at: float, args: argparse.Namespace, **extra) -> None:
    payload = {
        "status": status,
        "durationSec": round(time.time() - started_at, 3),
        "sourceVideo": args.video,
        "outputDir": args.output_dir,
        "skipPredict": bool(args.skip_tracknet),
        "largeVideo": bool(args.large_video),
        **extra,
    }
    write_json(path, payload)


if __name__ == "__main__":
    raise SystemExit(main())
