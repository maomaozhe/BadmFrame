# BadmFrame 重启计划

> 本文是历史重启计划和 2026-06-08 handoff 记录，不再作为最新执行顺序。当前事实入口见 [AGENTS.md](../AGENTS.md)，协作规则见 [Agent 工作流](../docs/agent-workflow.md)，领域方案见对应 `docs/` 文档。
> 2026-06-09 后续方向更新：主产品运行环境转向移动端本地自动剪辑，Web 主要作为链路验证、算法评估和调试平台。

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

## 阶段 3：多端 UI 对齐（历史口径）

旧口径曾把 Web 放在主产品体验前面。该口径已废弃，后续方向调整为移动端本地自动剪辑优先，Web 保留为验证和调试平台。

- Web：优先打磨播放器、时间线、候选列表、片段列表、导出弹窗。
- iOS：先同步设计结构和命名，短期不跑模型推理。
- 两端共享概念：Project、SourceVideo、Marker、Clip、RallyCandidate、ReviewState。
- 不做跨端数据同步，继续遵循 ADR-0002 的独立运行原则。

## Windows 开发建议

- 模型环境优先独立于主后端，可以用 Docker、Conda 或远端 GPU；主仓库只依赖标准 JSON I/O。
- Windows 上先确认 FFmpeg/FFprobe 可用，再跑视频元数据、抽帧和导出相关任务。
- 如果 TrackNetV3 环境难以本地复现，先用外部推理产物 JSON 接入评估脚本和 Web 审查台。
- 不提交大视频、模型权重、推理缓存或导出结果；只提交小标注文件、脚本、文档和必要代码。

## 历史下一步任务

以下条目来自重启早期计划，部分已经完成或被后续实现替代。后续继续工作时先以 `AGENTS.md` 和对应领域文档为准。

1. TrackNetV3 管线已接入，后续重点是权重/许可证/运行方式的交付确认。
2. `tools/evaluate_rallies.py` 已可评估 `rally_candidates.json`，后续需要更多人工标注视频，降低 `140.mp4` 过拟合风险。
3. 自动主场地/活动区域估计仍是后续优化方向。
4. Web 已有 rally candidate 审查工作流；AutoClip keep/cut 草稿保留为实验基线。
5. iOS/Web 统一 UI 信息架构仍可继续推进，但不是本文的最新执行清单。

## 2026-06-08 Handoff

Current branch/worktree:

- Main repo branch: `codex/model-tracknetv3-poc`
- Main repo commit: `e5c1966 feat: add rally job persistence, content dedup, and idempotency`
- Both `main` and `codex/model-tracknetv3-poc` point to the same commit (fast-forward merged).
- Worktree path: `E:\GitHub\youhua-heimadp\BadmFrame\.worktrees\model-tracknetv3-poc`

Changes since 2026-06-07:

- Merged `main` (10 commits) back into `codex/model-tracknetv3-poc`, bringing in:
  - `0d77cd7 feat: connect web workflow to backend`
  - Rally candidate contract tools, mock rally review workflow, Android MVP-A skeleton, docs
- **Rally job history**: Added `RallyJob` DB model and `rally_jobs` table (alembic 0003).
- **Content dedup**: Added `content_sha256` to `SourceVideo`, computed during upload.
- **Idempotency**: `POST /videos/{id}/rallies` checks for existing completed/running RallyJob before submitting new GPU work. Same video won't re-run TrackNetV3.
- **Task list endpoint**: `GET /videos/{id}/rallies` returns paginated rally detection history for a video.
- **MySQL compat**: Fixed TEXT column defaults in `0002_job_history.py` for MySQL strict mode.
- Frontend `npm run build` verified.

Fresh verification before commit:

- `server\.venv\Scripts\python.exe -m pytest tests -q` -> `54 passed`
- `model\.local\venv\Scripts\python.exe -m pytest model/tests -q` -> `22 passed`
- `cd web && npm run build` -> success
- `alembic upgrade head` -> `0003` reached (MySQL)

API endpoints (updated):

- `POST /api/v1/videos/{video_id}/rallies` — submit rally detection (idempotent)
- `GET /api/v1/videos/{video_id}/rallies` — list rally task history (new)
- `GET /api/v1/videos/{video_id}/rallies/{task_id}` — get result (syncs RallyJob status)
- `GET /api/v1/videos/{video_id}/rallies/{task_id}/progress` — poll progress
- `POST /api/v1/videos/{video_id}/rallies/import` — import external rally candidates
- `POST /api/v1/projects/{project_id}/rallies/apply` — apply accepted rallies as clips

Known follow-ups:

1. Push both the main repo branch and the TrackNetV3 submodule commit, or replace the submodule patch with an upstream-safe patching/setup step.
2. Re-test Web upload -> rally detection end to end after backend restart without `--reload`.
3. Add progress inside TrackNetV3 inference if users need more than stage-level progress during the 9-10 minute run.
4. Reduce false positives on the first 250s while preserving zero misses and sub-1s average boundary errors.
5. Collect at least one more annotated video; current `best_params.json` may overfit `140.mp4`.
6. Sync RallyJob status from the GPU thread on completion (currently synced on GET result, not on task finish).
