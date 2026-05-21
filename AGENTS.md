# BadmFrame Agent 指南

BadmFrame 是一个面向羽毛球场景的视频剪辑应用。技术架构已定（ADR-0002），即将进入 MVP 实现阶段。

这是编码 agent 的入口文档。接任务前先读本文件，再按下方链接阅读相关上下文。

## 当前状态

- 仓库状态：iOS、Web 前端、Web 后端 MVP 均已实现。
- 产品方向：面向羽毛球视频的剪辑和标注工具。
- MVP 方向：帮助业余爱好者导入自己录制的羽毛球视频，快速浏览并打时间点标记定位关键瞬间，裁剪片段，本地归档保存。
- 技术栈：已确定，见 [ADR-0002](docs/decisions/0002-technical-architecture.md)。
  - **iOS**：SwiftUI + AVFoundation + SwiftData（纯本地，零依赖）— 已实现 29 个源文件，待 Xcode 编译验证
  - **Web 前端**：React 19 + Tailwind v4 + shadcn/ui + Zustand — 已实现 28 个源文件，TypeScript 零错误，Vite 构建通过
  - **Web 后端**：FastAPI + MySQL + Redis + Celery + FFmpeg — 已实现 30+ 源文件，16 tests 通过，Alembic 迁移就绪

## 推荐阅读顺序

1. [产品上下文](docs/product.md)
2. [架构说明](docs/architecture.md)
3. [ADR-0002 技术架构决策](docs/decisions/0002-technical-architecture.md)
4. [视频处理流程](docs/video-pipeline.md)
5. [Agent 工作流](docs/agent-workflow.md)
6. [ADR-0001 上下文文档决策](docs/decisions/0001-project-context-docs.md)

## 开发约定

- 优先做小而清晰、容易回退的变更。
- 当代码变更影响产品行为、架构、命令或工作流时，同步更新文档。
- 项目上下文和决策记录使用 Markdown。
- 不要把大体积二进制文件，尤其是原始视频，直接提交到仓库，除非未来有明确策略。
- 优先服务真实的羽毛球复盘、教学和剪辑工作流，不要默认按通用视频剪辑器设计。

## 不要做

- 不要在没有 ADR 的情况下引入应用框架。
- 不要直接提交大体积媒体文件。
- 不要把 BadmFrame 当成通用短视频剪辑器，除非产品范围被明确修改。
- 不要覆盖用户工作或生成资产，除非已经确认其用途。
- 不要删除上下文文档，除非用更清晰的结构替代。

## 常用命令

命令随代码实现逐步补充。各端独立开发和构建。

```bash
# === iOS ===
# Xcode 打开 BadmFrame.xcodeproj 即可构建运行
# TODO: xcodebuild 命令行构建脚本

# === Web 前端（web/） ===
cd web
npm install
npm run dev        # Vite 开发服务器

# TODO: npm test
# TODO: npm run build

# === Web 后端（server/） ===
cd server
pip install -e ".[dev]"
uvicorn app.main:app --reload   # FastAPI 开发服务器

pytest
alembic upgrade head
```

## 当前已确定内容

- 项目从 agent 友好的文档结构开始。
- 文档以中文为主，命令和代码标识符保留英文。
- 第一阶段仍应先验证产品和技术选择，再进入核心应用代码开发。
- MVP 核心用户为业余爱好者，优先做时间点标记，主要场景为本地归档。

## 未决问题

- 多角度视频关联是否需要在 MVP 阶段支持？
- Web 端是否需要 Docker Compose 一键部署脚本？
- CI/CD 方案：iOS 端用 Xcode Cloud？Web 端用什么部署？
- Web 端是否需要用户系统，还是单机使用？

## Agent 注意事项

- 每个非简单任务开始前，先读本文件和最相关的链接文档。
- 新增重要决策时，在 `docs/decisions/` 下添加 ADR。
- 如果新增可运行代码，请更新上面的命令占位。
- 如果新增具有长期含义的目录，请同步更新 `docs/architecture.md`。

## 更新触发条件

出现以下情况时更新本文件：

- 技术栈被选定。
- 项目命令变成真实命令。
- 仓库结构发生变化。
- MVP 范围发生变化。
- Agent 工作流预期发生变化。
