from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "model"))

from badm_model.contracts import ShuttlePoint
from badm_model.io import ensure_dir, write_json
from badm_model.rally_refiner import RallyRefinerConfig
from badm_model.rally_tuner import WindowSegmentationConfig, tune_window_segmentation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tune window-based rally segmentation against manual annotations."
    )
    parser.add_argument("--input", required=True, help="Path to shuttle_points.json.")
    parser.add_argument("--annotations", required=True, help="Path to rally annotation JSON.")
    parser.add_argument("--output", required=True, help="Output directory.")
    parser.add_argument("--start-sec", type=float, default=0.0, help="Start time included in tuning.")
    parser.add_argument("--end-sec", type=float, default=None, help="End time included in tuning.")
    parser.add_argument("--window-sec", type=float, default=1.0)
    parser.add_argument("--step-sec", type=float, default=0.5)
    parser.add_argument("--min-rally-duration-sec", type=float, default=2.0)
    parser.add_argument("--refine", action="store_true", default=True, help="Apply boundary refiner (default: on).")
    parser.add_argument("--no-refine", action="store_false", dest="refine", help="Disable boundary refiner.")
    parser.add_argument("--refine-window", type=float, default=0.5, help="local_window_sec")
    parser.add_argument("--refine-step", type=float, default=0.25, help="local_step_sec")
    parser.add_argument("--refine-vis", type=float, default=0.20, help="min_visible_ratio for refiner")
    parser.add_argument("--refine-motion", type=float, default=280.0, help="min_motion_px_sec for refiner")
    parser.add_argument("--refine-spread", type=float, default=200.0, help="min_spread_px for refiner")
    parser.add_argument("--pre-match-grace", type=float, default=15.0)
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    annotations_path = Path(args.annotations)
    output_dir = ensure_dir(Path(args.output))

    shuttle_data = json.loads(input_path.read_text(encoding="utf-8"))
    annotation_data = json.loads(annotations_path.read_text(encoding="utf-8"))
    fps = float(shuttle_data.get("fps", 30.0))
    points = [
        ShuttlePoint(
            frameIndex=int(p["frameIndex"]),
            timeSec=float(p["timeSec"]),
            x=float(p["x"]),
            y=float(p["y"]),
            confidence=float(p.get("confidence", 0.0)),
            visible=bool(p.get("visible", False)),
            source=p.get("source", "tracknetv3"),
        )
        for p in shuttle_data.get("points", [])
    ]
    annotations = annotation_data.get("rallies") or annotation_data.get("annotations") or []

    refiner_config = None
    if args.refine:
        refiner_config = RallyRefinerConfig(
            local_window_sec=args.refine_window,
            local_step_sec=args.refine_step,
            min_visible_ratio=args.refine_vis,
            min_motion_px_sec=args.refine_motion,
            min_spread_px=args.refine_spread,
            pre_match_grace_sec=args.pre_match_grace,
        )

    result = tune_window_segmentation(
        points,
        fps,
        annotations=annotations,
        base_config=WindowSegmentationConfig(
            window_sec=args.window_sec,
            step_sec=args.step_sec,
            min_rally_duration_sec=args.min_rally_duration_sec,
            start_sec=args.start_sec,
            end_sec=args.end_sec,
        ),
        refiner_config=refiner_config,
    )

    candidates_path = output_dir / "rally_candidates.json"
    write_json(
        candidates_path,
        {
            "source": "tracknetv3+window_tuned",
            "sourceVideo": shuttle_data.get("sourceVideo", ""),
            "fps": fps,
            "tuning": {
                "config": asdict(result.config),
                "report": result.report,
                **({"refiner_config": asdict(result.refiner_config)} if result.refiner_config else {}),
            },
            "candidates": [
                {
                    "id": item.id,
                    "startSec": item.startSec,
                    "endSec": item.endSec,
                    "confidence": item.confidence,
                    "startReason": item.startReason,
                    "endReason": item.endReason,
                    "reviewState": item.reviewState,
                    "trajectoryStats": item.trajectoryStats,
                }
                for item in result.candidates
            ],
        },
    )
    write_json(output_dir / "tuning_report.json", {"config": asdict(result.config), "report": result.report})
    print(f"Wrote {len(result.candidates)} tuned rally candidates to {candidates_path}")
    print(
        "Best report: "
        f"recall={result.report['recall']:.4f}, "
        f"precision={result.report['precision']:.4f}, "
        f"boundaryError={result.report['boundaryErrorSec']['averageTotal']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
