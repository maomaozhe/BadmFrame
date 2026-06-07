from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "model"))

from badm_model.contracts import ShuttlePoint, ShuttlePointsResult
from badm_model.io import ensure_dir, write_json
from badm_model.rally_state_machine import RallyCandidate, RallyStateConfig, segment_rallies
from badm_model.trajectory_cleaner import clean_trajectory
from badm_model.trajectory_features import extract_features


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Segment shuttle_points.json into rally_candidates.json."
    )
    parser.add_argument(
        "--input", required=True, help="Path to shuttle_points.json."
    )
    parser.add_argument(
        "--output", required=True, help="Output directory for rally_candidates.json."
    )
    parser.add_argument(
        "--min-active-sec", type=float, default=0.5,
        help="Minimum active trajectory (seconds) to enter RallyActive state."
    )
    parser.add_argument(
        "--gap-tolerance-sec", type=float, default=0.5,
        help="Max gap between visible points to stay in same rally."
    )
    parser.add_argument(
        "--end-tolerance-sec", type=float, default=1.5,
        help="Time without ball to finalize rally end."
    )
    parser.add_argument(
        "--pre-buffer-sec", type=float, default=0.5,
        help="Extra seconds before rally start."
    )
    parser.add_argument(
        "--post-buffer-sec", type=float, default=1.0,
        help="Extra seconds after rally end."
    )
    parser.add_argument(
        "--min-rally-duration-sec", type=float, default=2.0,
        help="Minimum rally duration."
    )
    parser.add_argument(
        "--no-clean", action="store_true",
        help="Skip trajectory cleaning."
    )
    parser.add_argument(
        "--write-features", type=str, default=None,
        help="Optional path to write per-frame features JSON."
    )
    parser.add_argument(
        "--min-confidence", type=float, default=0.0,
        help="Minimum confidence to keep a rally candidate (0-1)."
    )
    parser.add_argument(
        "--min-visible-ratio", type=float, default=0.0,
        help="Minimum visible point ratio to keep a rally candidate (0-1)."
    )
    parser.add_argument(
        "--min-direction-changes", type=int, default=0,
        help="Minimum direction changes in a rally candidate."
    )
    parser.add_argument(
        "--end-visible-ratio", type=float, default=0.4,
        help="Visible ratio threshold in end_tolerance window to trigger rally end."
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    data = json.loads(input_path.read_text(encoding="utf-8"))
    points_data = data.get("points", [])
    fps = data.get("fps", 30.0)

    points = [
        ShuttlePoint(
            frameIndex=p["frameIndex"],
            timeSec=p["timeSec"],
            x=p["x"],
            y=p["y"],
            confidence=p.get("confidence", 0.0),
            visible=p.get("visible", False),
            source=p.get("source", "tracknetv3"),
        )
        for p in points_data
    ]

    # Optional cleaning
    if not args.no_clean:
        cleaned = clean_trajectory(
            points,
            max_gap_frames=int(args.gap_tolerance_sec * fps),
            frame_width=data.get("frameWidth"),
            frame_height=data.get("frameHeight"),
        )
        points = cleaned.points

    # Optional feature export
    if args.write_features:
        features = extract_features(points, fps)
        feature_path = Path(args.write_features)
        feature_path.parent.mkdir(parents=True, exist_ok=True)
        feature_path.write_text(
            json.dumps(
                {
                    "fps": features.fps,
                    "features": [
                        {
                            "frameIndex": f.frameIndex,
                            "timeSec": f.timeSec,
                            "visible": f.visible,
                            "visibleRatio": f.visibleRatio,
                            "maxGapSec": f.maxGapSec,
                            "directionChanges": f.directionChanges,
                            "meanSpeedPxSec": f.meanSpeedPxSec,
                            "nearBoundary": f.nearBoundary,
                            "isStationary": f.isStationary,
                        }
                        for f in features.features
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    # Run state machine
    config = RallyStateConfig(
        min_active_sec=args.min_active_sec,
        gap_tolerance_sec=args.gap_tolerance_sec,
        end_tolerance_sec=args.end_tolerance_sec,
        pre_buffer_sec=args.pre_buffer_sec,
        post_buffer_sec=args.post_buffer_sec,
        min_rally_duration_sec=args.min_rally_duration_sec,
        end_visible_ratio=args.end_visible_ratio,
    )
    result = segment_rallies(points, fps, config=config)

    # Post-filter candidates
    candidates = result.candidates
    if args.min_confidence > 0:
        candidates = [c for c in candidates if c.confidence >= args.min_confidence]
    if args.min_visible_ratio > 0:
        candidates = [c for c in candidates if c.trajectoryStats.get("visibleRatio", 0) >= args.min_visible_ratio]
    if args.min_direction_changes > 0:
        candidates = [c for c in candidates if c.trajectoryStats.get("directionChanges", 0) >= args.min_direction_changes]
    # Re-index after filtering
    candidates = [
        RallyCandidate(
            id=f"rally-{i + 1:03d}",
            startSec=c.startSec,
            endSec=c.endSec,
            confidence=c.confidence,
            startReason=c.startReason,
            endReason=c.endReason,
            reviewState=c.reviewState,
            trajectoryStats=c.trajectoryStats,
        )
        for i, c in enumerate(candidates)
    ]

    # Write output
    output_dir = ensure_dir(Path(args.output))
    out_path = output_dir / "rally_candidates.json"
    out_data = {
        "source": "tracknetv3+state_machine",
        "sourceVideo": data.get("sourceVideo", ""),
        "fps": fps,
        "candidates": [
            {
                "id": c.id,
                "startSec": c.startSec,
                "endSec": c.endSec,
                "confidence": c.confidence,
                "startReason": c.startReason,
                "endReason": c.endReason,
                "reviewState": c.reviewState,
                "trajectoryStats": c.trajectoryStats,
            }
            for c in candidates
        ],
    }
    write_json(out_path, out_data)
    print(f"Wrote {len(candidates)} rally candidates to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
