# BadmFrame 重启计划

## 目标

BadmFrame 重启后同时推进两件事：

- 核心能力：用模型生成羽毛球有效回合候选，用户确认后导出。
- 产品体验：优先做好 Web 审查工作台，同时让 iOS 在信息架构和视觉方向上保持一致。

第一阶段不承诺一键自动剪出最终视频。产品承诺是：系统尽量找出有效回合，用户快速确认、删除或微调边界，再导出。

## 当前基线

- 旧的全局运动量/音频启发式自动剪辑已暂停，只作为失败基线和对照实验保留。
- `video/140.mp4` 已有第一批人工 rally 标注：`assets/reference/rally_annotations_140.json`。
- Rally 评估脚本已完成：`tools/evaluate_rallies.py` 可对比人工标注和候选输出，报告召回、误报、边界误差、合并和碎片化；示例候选见 `server/tests/fixtures/rally_candidates.example.json`。
- Web 已有自动剪辑实验入口和合辑导出实验代码，但仍是本地模拟/启发式草稿，不代表最终产品能力。
- iOS 当前支持导入、播放、标记、片段和导出，暂不接模型。
- 当前 macOS 工作区缺少 FFmpeg、Docker、Conda；用户计划在 Windows 设备继续开发，且 Windows 环境可用于模型 POC。

## 阶段 1：模型 POC

目标：证明模型路线对真实羽毛球视频有希望。

- 建立独立模型推理器，不把 TrackNetV3/PyTorch 环境塞进现有 FastAPI venv。
- 输入视频，输出标准 JSON：`shuttle_points.json`、`court_estimate.json`、`rally_candidates.json`。
- 默认自动估计主场地或主活动区域；多场地误报时降低置信度，不要求用户手动画 ROI。
- 评估指标召回优先：主要有效回合尽量不漏，允许边界前后多留几秒和少量误报。
- 用 `assets/reference/rally_annotations_140.json` 和至少一段多场地球馆视频做评估。

用户需要做的事：

- 提供真实羽毛球视频，尤其是多场地球馆视频。
- 看候选回合结果，判断是否“基本能识别有效回合，达到可用”。

## 阶段 2：Web 审查工作台

目标：让模型结果能被用户快速修正，而不是黑盒自动导出。

- 编辑器主流程改为：分析 -> 候选回合 -> 审查 -> 确认片段 -> 导出。
- 时间线显示候选边界、置信度和错误原因。
- 候选列表支持确认、删除、微调起止、跳转播放。
- 已确认候选转为普通 clips，复用现有导出流程。
- 旧“自动剪辑”入口降级为实验/对照，不作为主入口。

## 阶段 3：多端 UI 对齐

目标：Web 先成为主产品体验，iOS 跟随同一套信息架构。

- Web：优先打磨播放器、时间线、候选列表、片段列表、导出弹窗。
- iOS：先同步设计结构和命名，短期不跑模型推理。
- 两端共享概念：Project、SourceVideo、Marker、Clip、RallyCandidate、ReviewState。
- 不做跨端数据同步，继续遵循 ADR-0002 的独立运行原则。

## Windows 开发建议

- 模型环境优先独立于主后端，可以用 Docker、Conda 或远端 GPU；主仓库只依赖标准 JSON I/O。
- Windows 上先确认 FFmpeg/FFprobe 可用，再跑视频元数据、抽帧和导出相关任务。
- 如果 TrackNetV3 环境难以本地复现，先用外部推理产物 JSON 接入评估脚本和 Web 审查台。
- 不提交大视频、模型权重、推理缓存或导出结果；只提交小标注文件、脚本、文档和必要代码。

## 下一步任务

1. 确认 TrackNetV3 权重、许可证与运行方式，产出第一份 `shuttle_points.json`。
2. 用 `tools/evaluate_rallies.py` 评估第一版 `rally_candidates.json`，优先看召回和漏检。
3. 做自动主场地/活动区域估计的 POC。
4. 将 Web 自动 tab 从 keep/cut 草稿改为 rally candidate 审查。
5. 输出 iOS/Web 统一 UI 信息架构草图。

## 2026-06-07 Handoff

Current branch/worktree:

- Main repo branch: `codex/model-tracknetv3-poc`
- Main repo commit: `7d47d9a Add TrackNetV3 rally detection pipeline`
- TrackNetV3 submodule local commit: `b9fb84e Allow loading TrackNet checkpoints on newer PyTorch`
- Worktree path: `E:\GitHub\youhua-heimadp\BadmFrame\.worktrees\model-tracknetv3-poc`

Implemented:

- `model/` now contains a standalone TrackNetV3 adapter and rally pipeline.
- `model/scripts/run_pipeline.py` runs: TrackNetV3 inference -> CSV conversion -> trajectory cleaning -> window segmentation -> `rally_candidates.json`.
- Web backend exposes rally APIs:
  - `POST /api/v1/videos/{video_id}/rallies`
  - `GET /api/v1/videos/{video_id}/rallies/{task_id}`
  - `GET /api/v1/videos/{video_id}/rallies/{task_id}/progress`
- Web frontend uploads browser-selected videos to the backend, starts rally detection, polls progress, and fills the auto clip panel with returned segments.
- Backend upload metadata extraction now falls back to OpenCV when `ffprobe` is unavailable. Export still needs FFmpeg.
- TrackNetV3 inference defaults are low-VRAM: `batch_size=1`, `eval_mode=nonoverlap`, `skip_inpaintnet=true`.

Validated on `E:\badm-video\140.mp4`:

- Full TrackNet-only inference completed in `562.286s`.
- Best first-250s evaluation output:
  - recall `1.0000`
  - precision `0.7619`
  - false positives `5`
  - missed rallies `0`
  - merged candidates `0`
  - fragmented rallies `0`
  - average start error `0.612s`
  - average end error `0.501s`
- Best local output path:
  `model/.local/runs/140_full_lowvram_skip_inpaint/window_tuned_250_grid/rally_candidates.json`

Fresh verification before commit:

- `server\.venv\Scripts\python.exe -m pytest tests -q` -> `32 passed`
- `model\.local\venv\Scripts\python.exe -m pytest model\tests -q` -> `22 passed`
- `cd web && npm run build` -> success
- `server/app/utils/ffmpeg.extract_metadata(E:\badm-video\140.mp4)` returns duration `651.4137s`, size `960x544`, fps `29.000002`.

Local run state for manual testing:

- Frontend: `http://127.0.0.1:5174`
- Backend health: `http://127.0.0.1:8000/health`
- Avoid `uvicorn --reload` while testing uploads because writes under `server/storage/` can trigger reloads.
- `server/storage/`, `.claude/`, `model/.local/`, and `model/configs/*.local.json` are local-only and should not be committed.

Known follow-ups:

1. Push both the main repo branch and the TrackNetV3 submodule commit, or replace the submodule patch with an upstream-safe patching/setup step.
2. Re-test Web upload -> rally detection end to end after backend restart without `--reload`.
3. Add progress inside TrackNetV3 inference if users need more than stage-level progress during the 9-10 minute run.
4. Reduce false positives on the first 250s while preserving zero misses and sub-1s average boundary errors.
5. Collect at least one more annotated video; current `best_params.json` may overfit `140.mp4`.
