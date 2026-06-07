# BadmFrame Model Layer

This directory contains BadmFrame's model adapter layer. The v1 goal is to run TrackNetV3, convert its CSV output into BadmFrame's standard `shuttle_points.json`, and tune a first-pass `rally_candidates.json` against manual annotations.

TrackNetV3 is included as a Git submodule at `model/vendor/TrackNetV3`. Model weights, local videos, generated CSV files, and run outputs stay outside git under `model/.local/`.

## Setup on Windows RTX 4050

```powershell
git submodule update --init --recursive

conda create -n tracknetv3 python=3.8
conda activate tracknetv3
cd model/vendor/TrackNetV3
pip install -r requirements.txt
```

The upstream README lists `torch==1.10.0`, but RTX 4050 machines may require a newer CUDA-compatible PyTorch build. Use the newest PyTorch/CUDA combination that imports `torch`, reports CUDA availability, and can run `predict.py`.

Download the TrackNetV3 checkpoints from the upstream README and place them here:

```text
model/.local/ckpts/
  TrackNet_best.pt
  InpaintNet_best.pt
```

Create a local config from the example:

```powershell
Copy-Item model/configs/tracknetv3.local.example.json model/configs/tracknetv3.local.json
```

Adjust paths if your checkout or checkpoint location differs.

## Run

From the repository root:

```powershell
python model/scripts/run_tracknetv3.py `
  --video E:\path\to\140.mp4 `
  --config model/configs/tracknetv3.local.json `
  --output-dir model/.local/runs/140 `
  --large-video `
  --skip-inpaintnet
```

Expected output:

```text
model/.local/runs/140/
  tracknet_raw/
    140_ball.csv
  shuttle_points.json
  run_metadata.json
```

For a dry conversion test without running TrackNetV3:

```powershell
python model/scripts/run_tracknetv3.py `
  --video E:\path\to\140.mp4 `
  --output-dir model/.local/runs/140-dry `
  --skip-predict `
  --tracknet-csv E:\path\to\140_ball.csv `
  --fps 30 `
  --frame-width 1920 `
  --frame-height 1080
```

## Tune Rally Candidates

After `shuttle_points.json` exists, tune a window-based rally segmenter against a manual annotation file:

```powershell
python model/scripts/tune_rally_segmentation.py `
  --input model/.local/runs/140/shuttle_points.json `
  --annotations assets/reference/rally_annotations_140.json `
  --output model/.local/runs/140/window_tuned_best_250 `
  --start-sec 0 `
  --end-sec 250 `
  --window-sec 0.8 `
  --step-sec 0.25
```

The tuner writes:

```text
model/.local/runs/140/window_tuned_best_250/
  rally_candidates.json
  tuning_report.json
```

For the local `140.mp4` TrackNet output and the current first-250s annotations, the best checked run uses:

```json
{
  "window_sec": 0.8,
  "step_sec": 0.25,
  "min_visible_ratio": 0.15,
  "min_motion_px_sec": 220.0,
  "min_spread_px": 260.0,
  "merge_gap_sec": 1.0,
  "pre_buffer_sec": 0.25,
  "post_buffer_sec": 0.0
}
```

Verification:

```powershell
python tools/evaluate_rallies.py `
  --annotations assets/reference/rally_annotations_140.json `
  --candidates model/.local/runs/140/window_tuned_best_250/rally_candidates.json `
  --output model/.local/runs/140/window_tuned_best_250/eval_report.json
```

Current local result for full TrackNet inference on `E:\badm-video\140.mp4` with `--skip-inpaintnet`, evaluated on the first 250 seconds: recall `1.0000`, precision `0.7619`, false positives `5`, merged candidates `0`, fragmented rallies `0`, average start error `0.612s`, average end error `0.501s`.

## Output Contract

`shuttle_points.json` uses this shape:

```json
{
  "sourceVideo": "E:\\path\\to\\140.mp4",
  "source": "tracknetv3",
  "fps": 30.0,
  "frameWidth": 1920,
  "frameHeight": 1080,
  "points": [
    {
      "frameIndex": 123,
      "timeSec": 4.1,
      "x": 512.0,
      "y": 218.0,
      "confidence": 1.0,
      "visible": true,
      "source": "tracknetv3"
    }
  ]
}
```

TrackNetV3 CSV has no confidence score. v1 maps visible points to `confidence: 1.0` and invisible points to `confidence: 0.0`.

## Scope

v1 generates offline `rally_candidates.json` from TrackNet output and annotation-guided tuning. It does not train models, does not import PyTorch into FastAPI, and does not connect to Web or iOS UI.
