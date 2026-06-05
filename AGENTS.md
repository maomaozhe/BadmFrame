# BadmFrame Agent 指南

BadmFrame 是面向羽毛球视频的剪辑和标注应用。MVP 已有 iOS、Web 前端、Web 后端三端实现；后续任务以维护一致性、验证真实工作流、补齐缺口为主。

## 快速状态

- 产品核心：业余爱好者导入羽毛球视频，快速浏览，打时间点标记，模型生成候选回合，用户确认后裁剪和本地归档。
- 技术架构：见 [ADR-0002](docs/decisions/0002-technical-architecture.md)。iOS 与 Web 独立运行，数据不同步。
- iOS：SwiftUI + AVFoundation + SwiftData，纯本地，零第三方依赖。命令行无签名构建可通过，仍需真机/模拟器交互验证。
- Web 前端：React 19 + Tailwind v4 + shadcn/ui + Zustand。`npm run build` 已验证通过。
- Web 后端：FastAPI + MySQL + Redis + Celery + FFmpeg。`server/.venv/bin/pytest` 已验证 20 tests 通过。
- E2E：Web 端已有 Playwright 套件，位于 `web/e2e/`，含 10 个 spec。

## 读文档策略

先读本文件，再按任务选择最少文档：

- 产品范围或交互取舍：读 [产品上下文](docs/product.md)。
- 目录、技术栈、跨端模型：读 [架构说明](docs/architecture.md)。
- 导入、预览、标记、裁剪、导出：读 [视频处理流程](docs/video-pipeline.md)。
- 自动剪掉捡球/等待等死球时间：读 [自动剪掉死球时间](docs/auto-dead-time-editing.md) 和 [ADR-0003](docs/decisions/0003-auto-dead-time-editing.md)。
- 新一版回合切分路线：读 [基于球轨迹的回合切分](docs/rally-segmentation.md) 和 [ADR-0004](docs/decisions/0004-rally-segmentation-by-shuttle-trajectory.md)。
- 重启后的执行顺序：读 [重启计划](tasks/restart-plan.md)。
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
```

## 开发约定

- 优先做小而清晰、容易回退的变更。
- 先检查当前仓库和未提交改动，再假设结构或状态。
- 行为变化要配套相关测试；命令、架构、产品行为或工作流变化要同步文档。
- 不要把 BadmFrame 当作通用短视频剪辑器，除非产品范围被明确修改。
- 不要提交大体积媒体、生成导出或本地缓存；测试媒体必须有明确用途并尽量小。
- 不要覆盖用户工作或生成资产，除非已经确认其用途。

## 当前未决

- 多角度视频关联是否进入 MVP 后续迭代。
- Web 端是否需要 Docker Compose 一键部署。
- CI/CD 方案。
- Web 端是否需要用户系统，还是保持单机/本地使用。
- 服务端 FFmpeg 并发导出策略。

## 更新触发条件

出现以下情况时更新本文件：技术栈、真实命令、仓库结构、MVP 范围、Agent 工作流预期发生变化。
