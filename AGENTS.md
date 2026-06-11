# BadmFrame Agent 指南

BadmFrame 是面向羽毛球视频的剪辑和标注应用。MVP 已有 iOS、Web 前端、Web 后端三端实现；后续任务以维护一致性、验证真实工作流、补齐缺口为主。

## 快速状态

- 产品核心：业余爱好者在移动端导入羽毛球视频，本地自动识别有效回合，边界误差目标小于 1s，用户确认后裁剪和本地归档。
- 技术架构：见 [ADR-0002](docs/decisions/0002-technical-architecture.md)。后续主运行环境是移动端，本地处理优先；Web 主要用于测通链路、评估算法和验证工作流，数据不同步。
- iOS：SwiftUI + AVFoundation + SwiftData，纯本地，零第三方依赖。命令行无签名构建可通过，仍需真机/模拟器交互验证。
- Web 前端：React 19 + Tailwind v4 + shadcn/ui + Zustand。最近已知 `npm run build` 可通过。
- Web 后端：FastAPI + MySQL + Redis + Celery + FFmpeg。最近已知 `server/.venv/bin/pytest` 有 54 tests 通过。
- E2E：Web 端已有 Playwright 套件，位于 `web/e2e/`，含 10 个 spec。
- Rally 评估闭环：`tools/evaluate_rallies.py` 已可对比人工标注与 `rally_candidates.json`，输出召回、误报、边界误差、合并和碎片化指标；后续优先补更多标注视频，降低单视频过拟合风险。
- 当前主路线：TrackNetV3 球轨迹候选回合 -> 边界误差评估（目标 < 1s）-> 用户审查 -> 确认后的 clips -> 复用导出流程。不要把未经确认的一键自动成片当作 MVP 承诺。
- 模型层：`model/` 已作为独立 TrackNetV3 适配层；官方 TrackNetV3 以 submodule 位于 `model/vendor/TrackNetV3`，权重、视频和推理输出放 `model/.local/` 且不入库。
  - **2026-06-08 幂等+历史追溯已实装**：`RallyJob` DB 表持久化任务状态，`content_sha256` 视频哈希去重，同视频重复提交不会重跑 GPU 推理。
  - **2026-06-07 管线已打通**：统一脚本 `model/scripts/run_pipeline.py` 串起 TrackNetV3 推理→CSV 转换→轨迹清理→窗口分割→输出 `rally_candidates.json`。
  - 最优窗口参数存于 `model/scripts/best_params.json`：merge_gap=1.0, vis=0.2, mot=220, spread=260。`E:\badm-video\140.mp4` 使用 TrackNet-only（`--skip-inpaintnet`）完整推理并评估前250s：recall=1.0, precision=0.7619, avg startErr=0.612s, avg endErr=0.501s。
  - RallyRefiner（`model/badm_model/rally_refiner.py`）边界精修方案已实现但未启用——局部重检测会降低召回率，当前不如直接调优窗口参数。
  - Web 后端已有 `server/app/services/rally_detection.py` 子进程管线调用和 `server/app/tasks/rally_detection.py` Celery 任务；当前公开 `server/app/api/rallies.py` 路由以候选导入、结果查询和应用为主，启动/进度查询仍需和真实工作流复测对齐。
  - **2026-06-08 AutoClip 死球时间分析已接入前端但不是主路线**：Web 前端第 5 个 tab "自动剪辑" 可用，后端提供异步分析启动、结果查询、项目分析列表/latest 和 apply 入口。该 FFmpeg 运动+音频启发式方案定位为实验/对照基线，不作为当前核心自动剪辑路线。
  - **TrackNetV3 推理耗时**：~12 分钟/10分钟视频（25 FPS），需要 NVIDIA GPU。MVP 阶段可跳过推理（`--skip-tracknet`），用已有 CSV 接管线。
  - 仅 1 个视频有手工标注（`assets/reference/rally_annotations_140.json`，16 回合），参数可能过拟合，后续需要更多标注视频。

## 读文档策略

先读本文件，再按任务选择最少文档：

- 产品范围或交互取舍：读 [产品上下文](docs/product.md)。
- 目录、技术栈、跨端模型：读 [架构说明](docs/architecture.md)。
- 导入、预览、标记、裁剪、导出：读 [视频处理流程](docs/video-pipeline.md)。
- 自动剪掉捡球/等待等死球时间：读 [自动剪掉死球时间](docs/auto-dead-time-editing.md) 和 [ADR-0003](docs/decisions/0003-auto-dead-time-editing.md)。
- 新一版回合切分路线：读 [基于球轨迹的回合切分](docs/rally-segmentation.md) 和 [ADR-0004](docs/decisions/0004-rally-segmentation-by-shuttle-trajectory.md)。
- 历史重启计划和交接记录：读 [重启计划](tasks/restart-plan.md)。该文件不再作为最新执行顺序，当前事实以本文件和相关领域文档为准。
- 工作方式、测试、ADR 触发条件：读 [Agent 工作流](docs/agent-workflow.md)。
- 重大技术决策：读 `docs/decisions/` 下相关 ADR。

不要把所有文档当作每个任务的固定前置；上下文越短，判断越稳定。

## 常用命令

```bash
# iOS
xcodebuild -project BadmFrame/BadmFrame.xcodeproj -scheme BadmFrame -configuration Debug -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build

# Web 前端
cd web
npm install
npm run dev
npm run build
npm run test:e2e

# Web 后端
cd server
pip install -e ".[dev]"
uvicorn app.main:app --reload
./.venv/bin/pytest
alembic upgrade head

# Rally 候选评估
python tools/evaluate_rallies.py \
  --annotations assets/reference/rally_annotations_140.json \
  --candidates server/tests/fixtures/rally_candidates.example.json

# 模型层：TrackNetV3 CSV -> shuttle_points.json dry run
python model/scripts/run_tracknetv3.py \
  --video /path/to/140.mp4 \
  --output-dir model/.local/runs/140-dry \
  --skip-predict \
  --tracknet-csv /path/to/140_ball.csv \
  --fps 30 \
  --frame-width 1920 \
  --frame-height 1080

# 模型层：完整管线（推理 → CSV 转换 → 清理 → 分割 → 输出）
python model/scripts/run_pipeline.py \
  --video /path/to/video.mp4 \
  --config model/configs/tracknetv3.local.json \
  --output-dir model/.local/runs/my-run/ \
  --progress-file model/.local/runs/my-run/progress.json

# 模型层：跳过推理的 dry run（用已有 CSV）
python model/scripts/run_pipeline.py \
  --video /path/to/video.mp4 \
  --output-dir model/.local/runs/dry-run/ \
  --skip-tracknet \
  --tracknet-csv /path/to/ball.csv \
  --fps 29 --frame-width 960 --frame-height 544

# 模型层：调参（可选 --refine 启用精修器）
python model/scripts/tune_rally_segmentation.py \
  --input model/.local/runs/140/shuttle_points.json \
  --annotations assets/reference/rally_annotations_140.json \
  --output model/.local/runs/140/tuned/ \
  --window-sec 0.8 --step-sec 0.25 \
  --end-sec 250
```

## 开发约定

- 回答之前加上：maomao
- 一个功能确定完成做好了就commit。
- 优先做小而清晰、容易回退的变更。
- 先检查当前仓库和未提交改动，再假设结构或状态。
- 行为变化要配套相关测试；命令、架构、产品行为或工作流变化要同步文档。
- 完成任务时说明目标、关键改动、验证命令和结果、未验证内容、剩余风险；长任务交接格式见 [Agent 工作流](docs/agent-workflow.md)。
- 不要把 BadmFrame 当作通用短视频剪辑器，除非产品范围被明确修改。
- 做架构选择时优先考虑移动端本地运行；Web 端新增能力应优先服务链路验证、评估和调试，而不是变成主产品依赖。
- 不要提交大体积媒体、生成导出或本地缓存；测试媒体必须有明确用途并尽量小。
- 不要覆盖用户工作或生成资产，除非已经确认其用途。

## 当前未决

- 服务端 FFmpeg 并发导出策略。

## 更新触发条件

出现以下情况时更新本文件：技术栈、真实命令、仓库结构、MVP 范围、Agent 工作流预期发生变化。
