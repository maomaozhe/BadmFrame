# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中工作时提供指导。

## 项目概述

BadmFrame 是一个面向羽毛球场景的视频剪辑应用——导入视频，找到有价值的片段，裁剪，添加简单标注，导出可分享的复盘视频。目标用户：业余爱好者、教练和内容创作者。

**当前阶段：** iOS 与 Web 前端 MVP 已实现，Web 后端待开发。

## Agent 入口

`AGENTS.md` 是所有编码 agent 的必读入口。接任务前先读它。

## 推荐阅读顺序

1. `docs/product.md` — 产品上下文、目标用户、MVP 范围和非目标
2. `docs/architecture.md` — 三端架构（iOS / Web 前端 / Web 后端）
3. `docs/decisions/0002-technical-architecture.md` — 技术栈决策记录
4. `docs/video-pipeline.md` — 媒体工作流规划
5. `docs/agent-workflow.md` — Agent 操作规则

## 技术架构总览

三端独立，数据不同步：

| 端 | 技术栈 | 说明 |
|---|--------|------|
| iOS | SwiftUI + AVFoundation + SwiftData（iOS 17+） | 纯本地，零服务端依赖，硬件加速 |
| Web 前端 | React 19 + Tailwind v4 + shadcn/ui + Zustand | Vite 构建，IndexedDB 本地缓存 |
| Web 后端 | FastAPI + MySQL 8.0 + Redis + Celery + FFmpeg | SQLAlchemy async、Alembic 迁移 |

## 关键约定

- **语言：** 文档以中文为主，命令和代码标识符保留英文。
- **无 ADR 不引入框架。** 重大技术决策必须记录到 `docs/decisions/`。
- **不要把 BadmFrame 当成通用视频剪辑器。** 产品选择应服务于羽毛球工作流。
- **不要提交大体积二进制/媒体文件**（视频等），除非有明确策略。
- **保持文档同步。** 代码变更影响架构、命令或工作流时，同步更新 `docs/architecture.md`。
- **优先做小而清晰、容易回退的变更。**
- 每次回答 以 maomao 开头

## 常用命令

```bash
# === iOS ===
# Xcode 打开 BadmFrame.xcodeproj 即可构建运行
# TODO: xcodebuild 命令行构建脚本

# === Web 前端（web/） ===
cd web && npm install
npm run dev              # Vite 开发服务器
# TODO: npm test
# TODO: npm run build

# === Web 后端（server/） ===
cd server && pip install -e ".[dev]"
uvicorn app.main:app --reload  # FastAPI 开发服务器
pytest
alembic upgrade head
```

## 目录结构

```
BadmFrame/
├── AGENTS.md                    # Agent 入口（必读）
├── CLAUDE.md                    # 本文件
├── docs/                        # 公共文档
│   ├── product.md
│   ├── architecture.md          # 三端架构说明
│   ├── video-pipeline.md
│   ├── agent-workflow.md
│   └── decisions/               # ADR
├── BadmFrame/                   # iOS 源码（SwiftUI）
├── web/                         # Web 前端（React）
├── server/                      # Web 后端（FastAPI）
└── tasks/                       # 任务规划预留
```

## 未决问题

- Web 端是否需要 Docker Compose 一键部署？
- CI/CD 方案？
- Web 端是否需要用户系统？
