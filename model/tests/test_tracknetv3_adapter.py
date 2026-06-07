from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "model"))

from badm_model.tracknetv3_adapter import TrackNetV3Config, convert_tracknet_csv, run_tracknetv3_predict
from badm_model.video_metadata import VideoMetadata


class TrackNetV3AdapterTests(unittest.TestCase):
    def test_converts_tracknet_csv_to_shuttle_points_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "140_ball.csv"
            _write_csv(
                csv_path,
                [
                    {"Frame": "0", "Visibility": "1", "X": "10", "Y": "20"},
                    {"Frame": "45", "Visibility": "0", "X": "0", "Y": "0"},
                ],
            )

            result = convert_tracknet_csv(
                csv_path=csv_path,
                video_path=Path(r"E:\videos\140.mp4"),
                metadata=VideoMetadata(fps=30.0, frame_width=1920, frame_height=1080, frame_count=90),
            )

        self.assertEqual(result.sourceVideo, r"E:\videos\140.mp4")
        self.assertEqual(result.source, "tracknetv3")
        self.assertEqual(result.fps, 30.0)
        self.assertEqual(result.frameWidth, 1920)
        self.assertEqual(result.frameHeight, 1080)
        self.assertEqual(len(result.points), 2)
        self.assertEqual(result.points[0].frameIndex, 0)
        self.assertEqual(result.points[0].timeSec, 0.0)
        self.assertEqual(result.points[0].x, 10.0)
        self.assertEqual(result.points[0].y, 20.0)
        self.assertEqual(result.points[0].confidence, 1.0)
        self.assertTrue(result.points[0].visible)
        self.assertEqual(result.points[1].frameIndex, 45)
        self.assertEqual(result.points[1].timeSec, 1.5)
        self.assertEqual(result.points[1].confidence, 0.0)
        self.assertFalse(result.points[1].visible)

    def test_rejects_csv_missing_required_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "bad.csv"
            _write_csv(csv_path, [{"Frame": "0", "Visibility": "1", "X": "10"}])

            with self.assertRaisesRegex(ValueError, "Missing required TrackNet CSV columns: Y"):
                convert_tracknet_csv(
                    csv_path=csv_path,
                    video_path=Path("video.mp4"),
                    metadata=VideoMetadata(fps=30.0, frame_width=1920, frame_height=1080, frame_count=1),
                )

    def test_cli_skip_predict_converts_existing_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "140_ball.csv"
            video_path = tmp_path / "140.mp4"
            output_dir = tmp_path / "run"
            video_path.write_bytes(b"fake video for dry run")
            _write_csv(csv_path, [{"Frame": "45", "Visibility": "1", "X": "100", "Y": "200"}])

            script = ROOT / "model" / "scripts" / "run_tracknetv3.py"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--video",
                    str(video_path),
                    "--output-dir",
                    str(output_dir),
                    "--skip-predict",
                    "--tracknet-csv",
                    str(csv_path),
                    "--fps",
                    "30",
                    "--frame-width",
                    "1920",
                    "--frame-height",
                    "1080",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((output_dir / "shuttle_points.json").read_text(encoding="utf-8"))
            metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))

        self.assertEqual(result["points"][0]["timeSec"], 1.5)
        self.assertEqual(result["points"][0]["visible"], True)
        self.assertEqual(metadata["status"], "completed")
        self.assertTrue(metadata["skipPredict"])

    def test_run_tracknetv3_predict_executes_predict_from_submodule_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "TrackNetV3"
            repo.mkdir()
            video_path = tmp_path / "140.mp4"
            tracknet_checkpoint = tmp_path / "TrackNet_best.pt"
            inpaintnet_checkpoint = tmp_path / "InpaintNet_best.pt"
            video_path.write_bytes(b"fake video")
            tracknet_checkpoint.write_bytes(b"checkpoint")
            inpaintnet_checkpoint.write_bytes(b"checkpoint")
            (repo / "predict.py").write_text(
                "\n".join(
                    [
                        "import argparse, csv",
                        "from pathlib import Path",
                        "parser = argparse.ArgumentParser()",
                        "parser.add_argument('--video_file')",
                        "parser.add_argument('--tracknet_file')",
                        "parser.add_argument('--inpaintnet_file')",
                        "parser.add_argument('--save_dir')",
                        "parser.add_argument('--eval_mode', default='nonoverlap')",
                        "parser.add_argument('--batch_size', type=int, default=1)",
                        "parser.add_argument('--large_video', action='store_true')",
                        "args = parser.parse_args()",
                        "out = Path(args.save_dir)",
                        "out.mkdir(parents=True, exist_ok=True)",
                        "with (out / (Path(args.video_file).stem + '_ball.csv')).open('w', newline='', encoding='utf-8') as handle:",
                        "    writer = csv.DictWriter(handle, fieldnames=['Frame', 'Visibility', 'X', 'Y'])",
                        "    writer.writeheader()",
                        "    writer.writerow({'Frame': '0', 'Visibility': '1', 'X': '10', 'Y': '20'})",
                    ]
                ),
                encoding="utf-8",
            )

            run = run_tracknetv3_predict(
                video_path=video_path,
                output_dir=tmp_path / "run",
                config=TrackNetV3Config(
                    tracknet_repo=repo,
                    tracknet_checkpoint=tracknet_checkpoint,
                    inpaintnet_checkpoint=inpaintnet_checkpoint,
                    python=sys.executable,
                ),
                large_video=True,
            )

            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.command[1], "predict.py")
            self.assertTrue(run.csv_path.exists())

    def test_run_tracknetv3_predict_passes_video_path_compatible_with_upstream_name_parser(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "TrackNetV3"
            repo.mkdir()
            source_dir = tmp_path / "source videos"
            source_dir.mkdir()
            video_path = source_dir / "140.mp4"
            tracknet_checkpoint = tmp_path / "TrackNet_best.pt"
            video_path.write_bytes(b"fake video")
            tracknet_checkpoint.write_bytes(b"checkpoint")
            (repo / "predict.py").write_text(
                "\n".join(
                    [
                        "import argparse, csv, os",
                        "parser = argparse.ArgumentParser()",
                        "parser.add_argument('--video_file')",
                        "parser.add_argument('--tracknet_file')",
                        "parser.add_argument('--save_dir')",
                        "parser.add_argument('--eval_mode', default='nonoverlap')",
                        "parser.add_argument('--batch_size', type=int, default=1)",
                        "args = parser.parse_args()",
                        "os.makedirs(args.save_dir, exist_ok=True)",
                        "video_name = args.video_file.split('/')[-1][:-4]",
                        "out_csv_file = os.path.join(args.save_dir, f'{video_name}_ball.csv')",
                        "os.makedirs(os.path.dirname(out_csv_file), exist_ok=True)",
                        "with open(out_csv_file, 'w', newline='', encoding='utf-8') as handle:",
                        "    writer = csv.DictWriter(handle, fieldnames=['Frame', 'Visibility', 'X', 'Y'])",
                        "    writer.writeheader()",
                        "    writer.writerow({'Frame': '0', 'Visibility': '1', 'X': '10', 'Y': '20'})",
                    ]
                ),
                encoding="utf-8",
            )

            run = run_tracknetv3_predict(
                video_path=video_path,
                output_dir=tmp_path / "run",
                config=TrackNetV3Config(
                    tracknet_repo=repo,
                    tracknet_checkpoint=tracknet_checkpoint,
                    python=sys.executable,
                ),
            )

            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(run.csv_path.exists())
            self.assertEqual(run.csv_path.parent, tmp_path / "run" / "tracknet_raw")


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
