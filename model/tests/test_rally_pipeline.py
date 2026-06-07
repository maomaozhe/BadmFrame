from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "model"))

from badm_model.contracts import ShuttlePoint
from badm_model.rally_state_machine import RallyStateConfig, RallyStateResult, segment_rallies
from badm_model.rally_tuner import (
    WindowSegmentationConfig,
    _score_report,
    generate_window_candidates,
    tune_window_segmentation,
)
from badm_model.trajectory_cleaner import clean_trajectory
from badm_model.trajectory_features import extract_features


# ── Helpers ────────────────────────────────────────────────────────


def _make_point(
    frame: int, x: float, y: float, visible: bool, fps: float = 30.0
) -> ShuttlePoint:
    return ShuttlePoint(
        frameIndex=frame,
        timeSec=round(frame / fps, 6),
        x=x,
        y=y,
        confidence=1.0 if visible else 0.0,
        visible=visible,
    )


def _make_visible_sequence(
    start_frame: int, count: int, fps: float = 30.0
) -> list[ShuttlePoint]:
    return [
        _make_point(start_frame + i, 500.0 + i, 300.0 + i, True, fps)
        for i in range(count)
    ]


# ── Trajectory cleaner tests ───────────────────────────────────────


class TrajectoryCleanerTests(unittest.TestCase):
    def test_cleaner_passes_through_visible_sequence(self) -> None:
        points = _make_visible_sequence(0, 30)
        result = clean_trajectory(points)
        self.assertEqual(len(result.points), 30)
        self.assertEqual(result.removedCount, 0)

    def test_cleaner_fills_short_gap(self) -> None:
        fps = 30.0
        # 5 visible, 3 invisible, 5 visible
        points = _make_visible_sequence(0, 5, fps)
        points += [_make_point(i, 0, 0, False, fps) for i in range(5, 8)]
        points += _make_visible_sequence(8, 5, fps)
        result = clean_trajectory(points, max_gap_frames=5)
        # Short gap should be filled
        self.assertEqual(len(result.points), 13)
        self.assertTrue(result.points[6].visible)  # interpolated
        self.assertEqual(result.points[6].confidence, 0.5)

    def test_cleaner_keeps_large_gap(self) -> None:
        fps = 30.0
        points = _make_visible_sequence(0, 5, fps)
        points += [_make_point(i, 0, 0, False, fps) for i in range(5, 20)]
        points += _make_visible_sequence(20, 5, fps)
        result = clean_trajectory(points, max_gap_frames=5)
        # Large gap should NOT be filled
        invisible = [p for p in result.points if not p.visible]
        self.assertGreater(len(invisible), 0)

    def test_cleaner_clamps_oob(self) -> None:
        points = [
            _make_point(0, 500, 300, True),
            _make_point(1, 10000, 300, True),  # way outside
            _make_point(2, 500, 300, True),
        ]
        result = clean_trajectory(points, frame_width=1920, frame_height=1080, max_gap_frames=0)
        # With max_gap_frames=0, no interpolation fills happen.
        # The OOB point stays invisible since gap fill is disabled.
        self.assertFalse(result.points[1].visible)

    def test_cleaner_empty_input(self) -> None:
        result = clean_trajectory([])
        self.assertEqual(len(result.points), 0)


# ── Trajectory features tests ──────────────────────────────────────


class TrajectoryFeaturesTests(unittest.TestCase):
    def test_feature_extraction_basic(self) -> None:
        points = _make_visible_sequence(0, 60)
        feat = extract_features(points, fps=30.0)
        self.assertEqual(len(feat.features), 60)
        self.assertGreater(feat.features[30].visibleRatio, 0.9)
        self.assertAlmostEqual(feat.features[30].maxGapSec, 0.0)

    def test_feature_detects_gap(self) -> None:
        fps = 30.0
        points = _make_visible_sequence(0, 15, fps)
        points += [_make_point(i, 0, 0, False, fps) for i in range(15, 20)]
        points += _make_visible_sequence(20, 15, fps)
        feat = extract_features(points, fps=fps, window_frames=30)
        # Points near the gap should show reduced visibleRatio
        gap_features = feat.features[15:20]
        for f in gap_features:
            self.assertLess(f.visibleRatio, 1.0)


# ── Rally state machine tests ──────────────────────────────────────


class RallyStateMachineTests(unittest.TestCase):
    def test_empty_points(self) -> None:
        result = segment_rallies([], fps=30.0)
        self.assertEqual(len(result.candidates), 0)

    def test_single_continuous_rally(self) -> None:
        points = _make_visible_sequence(0, 300)
        result = segment_rallies(points, fps=30.0)
        self.assertGreaterEqual(len(result.candidates), 1)

    def test_two_rallies_with_long_gap(self) -> None:
        fps = 30.0
        points = _make_visible_sequence(0, 200, fps)
        points += [_make_point(i, 0, 0, False, fps) for i in range(200, 350)]
        points += _make_visible_sequence(350, 200, fps)
        result = segment_rallies(points, fps=fps, config=RallyStateConfig(
            end_tolerance_sec=2.0,
            min_active_sec=0.3,
        ))
        self.assertGreaterEqual(len(result.candidates), 2)

    def test_rally_with_short_gap_stays_connected(self) -> None:
        fps = 30.0
        points = _make_visible_sequence(0, 100, fps)
        points += [_make_point(i, 0, 0, False, fps) for i in range(100, 115)]
        points += _make_visible_sequence(115, 100, fps)
        result = segment_rallies(points, fps=fps, config=RallyStateConfig(
            end_tolerance_sec=2.0,
            gap_tolerance_sec=1.0,
        ))
        # 15 frames = 0.5 sec gap at 30fps. Should remain 1 rally
        self.assertEqual(len(result.candidates), 1)

    def test_candidate_has_correct_shape(self) -> None:
        points = _make_visible_sequence(0, 300)
        result = segment_rallies(points, fps=30.0)
        c = result.candidates[0]
        self.assertIsInstance(c.id, str)
        self.assertGreater(c.endSec, c.startSec)
        self.assertGreaterEqual(c.confidence, 0.0)
        self.assertLessEqual(c.confidence, 1.0)
        self.assertEqual(c.reviewState, "pending")
        self.assertIn("visibleRatio", c.trajectoryStats)
        self.assertIn("directionChanges", c.trajectoryStats)

    def test_short_rally_filtered(self) -> None:
        points = _make_visible_sequence(0, 30)
        result = segment_rallies(points, fps=30.0, config=RallyStateConfig(
            min_rally_duration_sec=2.0,
            min_active_sec=0.3,
        ))
        # 30 frames = 1 sec at 30fps, below 2 sec minimum
        self.assertEqual(len(result.candidates), 0)


# ── CLI integration test ───────────────────────────────────────────


class RallyWindowTunerTests(unittest.TestCase):
    def test_score_prefers_unmerged_candidates_over_higher_precision_merged_candidate(self) -> None:
        merged = {
            "recall": 1.0,
            "precision": 1.0,
            "mergedCandidates": 1,
            "fragmentedRallies": 0,
            "boundaryErrorSec": {"averageTotal": 200.0},
            "totalCandidates": 1,
            "falsePositives": 0,
        }
        split = {
            "recall": 1.0,
            "precision": 0.8,
            "mergedCandidates": 0,
            "fragmentedRallies": 0,
            "boundaryErrorSec": {"averageTotal": 5.0},
            "totalCandidates": 17,
            "falsePositives": 4,
        }

        self.assertGreater(
            _score_report(split, annotation_count=16),
            _score_report(merged, annotation_count=16),
        )

    def test_window_segmentation_ignores_stationary_false_tracks(self) -> None:
        fps = 10.0
        points: list[ShuttlePoint] = []
        for frame in range(300):
            sec = frame / fps
            active = (5 <= sec < 10) or (20 <= sec < 25)
            stationary_false_track = 12 <= sec < 18
            visible = active or stationary_false_track
            if active:
                x = 300 + (frame % 20) * 12
                y = 200 + (frame % 10) * 8
            elif stationary_false_track:
                x = 600
                y = 420
            else:
                x = 0
                y = 0
            points.append(_make_point(frame, x, y, visible, fps))

        candidates = generate_window_candidates(
            points,
            fps,
            WindowSegmentationConfig(
                window_sec=1.0,
                step_sec=0.5,
                min_visible_ratio=0.5,
                min_motion_px_sec=50,
                min_spread_px=30,
                merge_gap_sec=1.0,
                min_rally_duration_sec=2.0,
                pre_buffer_sec=0.0,
                post_buffer_sec=0.0,
            ),
        )

        self.assertEqual(len(candidates), 2)
        self.assertEqual([c.id for c in candidates], ["rally-001", "rally-002"])
        self.assertAlmostEqual(candidates[0].startSec, 5.0, delta=0.75)
        self.assertAlmostEqual(candidates[0].endSec, 10.0, delta=0.75)
        self.assertAlmostEqual(candidates[1].startSec, 20.0, delta=0.75)
        self.assertAlmostEqual(candidates[1].endSec, 25.0, delta=0.75)

    def test_tuner_selects_parameters_with_better_annotation_score(self) -> None:
        fps = 10.0
        points: list[ShuttlePoint] = []
        for frame in range(300):
            sec = frame / fps
            active = (5 <= sec < 10) or (20 <= sec < 25)
            stationary_false_track = 12 <= sec < 18
            visible = active or stationary_false_track
            x = 300 + (frame % 20) * 12 if active else (600 if visible else 0)
            y = 200 + (frame % 10) * 8 if active else (420 if visible else 0)
            points.append(_make_point(frame, x, y, visible, fps))

        result = tune_window_segmentation(
            points,
            fps,
            annotations=[
                {"id": "rally-001", "startSec": 5.0, "endSec": 10.0},
                {"id": "rally-002", "startSec": 20.0, "endSec": 25.0},
            ],
            base_config=WindowSegmentationConfig(
                window_sec=1.0,
                step_sec=0.5,
                min_visible_ratio=0.5,
                merge_gap_sec=10.0,
                min_rally_duration_sec=2.0,
                pre_buffer_sec=0.0,
                post_buffer_sec=0.0,
            ),
            min_motion_grid=[0.0, 50.0],
            min_spread_grid=[0.0, 30.0],
            merge_gap_grid=[1.0, 10.0],
        )

        self.assertEqual(result.report["matchedRallies"], 2)
        self.assertEqual(result.report["falsePositives"], 0)
        self.assertEqual(len(result.candidates), 2)
        self.assertGreaterEqual(result.config.min_motion_px_sec, 50.0)


class SegmentRalliesCLITests(unittest.TestCase):
    def test_cli_segments_shuttle_points(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Write a shuttle_points.json
            # Gap of 200 frames (6.67s) between the two visible segments,
            # enough for windowed end-detection (end_tolerance_sec=3.0 default).
            points = []
            fps = 30.0
            for i in range(750):  # 25 seconds
                visible = (50 <= i < 250) or (450 <= i < 650)
                x = 500.0 if visible else 0.0
                y = 300.0 if visible else 0.0
                points.append(
                    {
                        "frameIndex": i,
                        "timeSec": round(i / fps, 6),
                        "x": x,
                        "y": y,
                        "confidence": 1.0 if visible else 0.0,
                        "visible": visible,
                        "source": "tracknetv3",
                    }
                )
            input_path = tmp_path / "shuttle_points.json"
            input_path.write_text(
                json.dumps(
                    {
                        "sourceVideo": "test.mp4",
                        "source": "tracknetv3",
                        "fps": fps,
                        "frameWidth": 1920,
                        "frameHeight": 1080,
                        "points": points,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            script = ROOT / "model" / "scripts" / "segment_rallies.py"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--input", str(input_path),
                    "--output", str(tmp_path),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            out = json.loads((tmp_path / "rally_candidates.json").read_text(encoding="utf-8"))
            self.assertIn("candidates", out)
            # Should detect 2 rallies
            self.assertGreaterEqual(len(out["candidates"]), 2)


if __name__ == "__main__":
    unittest.main()
