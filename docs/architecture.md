# 架构说明

BadmFrame 的架构由 [ADR-0002](decisions/0002-technical-architecture.md) 决定，本文档是架构的持续记录。

## 平台与总体架构

BadmFrame 由三个独立部分组成：

```
┌─────────────────────────────┐     ┌──────────────────────────────────────┐
│         iOS App              │     │              Web 端                   │
│  SwiftUI + AVFoundation      │     │                                      │
│  SwiftData（本地持久化）      │     │  ┌──────────┐     ┌──────────────┐  │
│  视频处理：硬件加速、纯本地    │     │  │ React 19 │ ←─→ │ FastAPI      │  │
│  零服务端依赖                 │     │  │ Tailwind │     │ MySQL+Redis  │  │
└─────────────────────────────┘     │  │ shadcn/ui│     │ FFmpeg       │  │
                                    │  └──────────┘     └──────────────┘  │
                                    └──────────────────────────────────────┘
```

- **iOS 端**：纯本地应用，AVFoundation 硬件加速处理视频，SwiftData 本地存储
- **Web 端**：前后端分离，前端 React 在浏览器中播放/标记，后端 FastAPI 负责视频处理和持久化
- **两端独立运行**，数据不同步，用户在哪端操作就在哪端完成全流程

## iOS 端（SwiftUI + AVFoundation + SwiftData）

| 操作 | 方案 | 框架 |
|------|------|------|
| 视频导入 | PHPicker 选择 → 拷贝到 App 沙盒 | PhotosUI |
| 元数据提取 | 异步加载 duration/resolution/codec/VFR | AVAsset |
| 播放 | 硬件解码 H.264/HEVC | AVPlayer |
| 缩略图 | 间隔抽帧 → sprite sheet 缓存 | AVAssetImageGenerator |
| 片段导出 | 硬件加速，默认 stream copy | AVAssetExportSession |
| 数据存储 | ORM，自动迁移 | SwiftData（iOS 17+） |

**架构模式**：MVVM，ViewModel 用 `@Observable` 宏

**目录结构**：
```
BadmFrame/
├── BadmFrame.xcodeproj
├── BadmFrame/
│   ├── App/                         # 入口
│   ├── Models/                      # @Model 类（Project, Marker, Clip...）
│   ├── ViewModels/                  # @Observable ViewModel
│   ├── Views/                       # SwiftUI 视图
│   │   ├── Projects/                # 项目列表 + 导入
│   │   ├── Editor/                  # 编辑主界面 + 播放器
│   │   ├── Timeline/                # 时间线（canvas 渲染）
│   │   ├── Markers/                 # 标记面板
│   │   ├── Clips/                   # 片段面板
│   │   ├── Export/                  # 导出
│   │   └── Common/                  # 通用组件
│   ├── Services/                    # 导入、缩略图、导出、存储
│   └── Extensions/                  # 工具扩展
└── docs/
```

**零第三方依赖**，全部使用 Apple 系统框架。

## Web 前端（React 19 + Tailwind v4 + shadcn/ui + Zustand）

| 层级 | 选型 |
|------|------|
| 框架 | React 19 + TypeScript |
| 样式 | Tailwind CSS v4（`@theme` 定义 token） |
| 组件库 | shadcn/ui（Radix 无样式原语） |
| 状态管理 | Zustand（project/video/marker/clip/ui 五个 slice） |
| 构建 | Vite |
| 图标 | lucide-react |
| 视频播放 | HTML5 `<video>` 元素直读源文件 |
| 缩略图 | `<video>` + `<canvas>` 提取帧 |
| 本地缓存 | IndexedDB（项目元数据前端缓存） |

**目录结构**：
```
web/
├── src/
│   ├── index.css                    # Tailwind 入口
│   ├── types.ts                     # 与后端对齐的数据模型
│   ├── components/
│   │   ├── ui/                      # shadcn/ui 组件
│   │   ├── ProjectList/
│   │   ├── Editor/                  # VideoPlayer + Controls
│   │   ├── Timeline/                # 时间线 + 缩略图条 + 标记层 + 裁剪层
│   │   ├── Markers/
│   │   ├── Clips/
│   │   └── Export/
│   ├── store/                       # Zustand slices
│   ├── hooks/                       # 视频播放、键盘快捷键、时间线、导出
│   ├── services/                    # HTTP 客户端、WebSocket 客户端
│   └── utils/
├── e2e/                           # Playwright 端到端测试
│   ├── tests/                     # 核心 Web 工作流测试
│   ├── helpers/                   # 页面、IndexedDB、截图辅助
│   └── fixtures/                  # 测试视频（尽量小，避免大媒体进入 git）
└── playwright.config.ts
```

## Web 后端（FastAPI + MySQL + Redis + FFmpeg）

| 组件 | 选型 | 用途 |
|------|------|------|
| Web 框架 | FastAPI | 异步、WebSocket、自动 OpenAPI |
| ORM | SQLAlchemy 2.0 (async) | MySQL 异步操作 |
| 数据库 | MySQL 8.0 | 项目、标记、片段、导出任务 |
| 缓存/队列 | Redis | 导出队列、进度缓存、上传状态 |
| 任务队列 | Celery（Redis broker） | 导出任务异步执行 |
| 视频处理 | FFmpeg（subprocess） | 元数据、缩略图、导出 |
| 文件存储 | 本地磁盘 + 定时清理 | 上传/缩略图/导出 |
| 迁移 | Alembic | 数据库 schema 版本管理 |

## 模型推理层（重启后新增方向）

自动剪辑不再依赖主后端内的全局运动量启发式方案。模型推理应作为独立运行层接入：

- 输入：源视频路径、抽帧配置、可选调试 ROI 配置。
- 输出：`shuttle_points.json`、`court_estimate.json`、`rally_candidates.json`。
- 运行环境：优先独立于 FastAPI venv，可在 Windows 上使用 Docker、Conda 或远端 GPU。
- 主后端只消费标准 JSON 结果，并负责保存任务状态、候选回合和用户审查结果。
- 产品主路径不要求用户手动画 ROI；需要自动估计主场地或主活动区域。

**API 路由**：
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/videos/upload` | 上传视频 |
| GET | `/api/v1/videos/{id}` | 视频元数据 |
| POST | `/api/v1/projects` | 创建项目 |
| GET | `/api/v1/projects` | 项目列表 |
| GET | `/api/v1/projects/{id}` | 项目详情（含 markers, clips） |
| PUT | `/api/v1/projects/{id}` | 更新项目 |
| DELETE | `/api/v1/projects/{id}` | 删除项目 |
| POST | `/api/v1/projects/{pid}/markers` | 创建标记 |
| PUT | `/api/v1/projects/{pid}/markers/{id}` | 更新标记 |
| DELETE | `/api/v1/projects/{pid}/markers/{id}` | 删除标记 |
| POST | `/api/v1/projects/{pid}/clips` | 创建片段 |
| PUT | `/api/v1/projects/{pid}/clips/{id}` | 更新片段 |
| DELETE | `/api/v1/projects/{pid}/clips/{id}` | 删除片段 |
| POST | `/api/v1/exports` | 提交导出任务 |
| GET | `/api/v1/exports/{task_id}` | 查询状态 |
| WS | `/ws/exports/{task_id}` | 实时进度推送 |
| GET | `/api/v1/exports/{task_id}/download` | 下载结果 |
| DELETE | `/api/v1/exports/{task_id}` | 取消任务 |

**目录结构**：
```
server/
├── pyproject.toml
├── alembic.ini
├── app/
│   ├── main.py                     # 入口
│   ├── config.py                   # 配置
│   ├── database.py                 # DB 连接
│   ├── models/                     # SQLAlchemy ORM
│   ├── schemas/                    # Pydantic
│   ├── api/                        # 路由
│   ├── services/                   # 业务逻辑（视频、导出、缩略图、存储）
│   ├── tasks/                      # Celery 异步任务
│   └── utils/                      # FFmpeg 封装、Redis 客户端
├── storage/                        # 文件存储（gitignore）
└── tests/
```

## 数据模型（两端对齐）

| 实体 | iOS 存储 | Web 存储 |
|------|----------|----------|
| Project | SwiftData | MySQL |
| Marker | SwiftData | MySQL |
| Clip | SwiftData | MySQL |
| SourceVideo | 沙盒文件路径 | 服务器文件路径 + MySQL 记录 |
| 导出任务 | 本地 runloop | Celery + Redis + MySQL |

核心字段：`Project { id, name, sourceVideo, markers[], clips[] }`、`Marker { id, timestampSec, label, color }`、`Clip { id, startTimeSec, endTimeSec, label, notes, anchorMarkerId, exportStatus }`。

详细定义见各端 `types.ts` / `Models/`。

## 视频处理策略（两端对比）

| 操作 | iOS | Web |
|------|-----|-----|
| 播放 | AVPlayer 硬件解码 | HTML5 `<video>` 浏览器解码 |
| 缩略图 | AVAssetImageGenerator | `<video>` + `<canvas>` |
| 导出 | AVAssetExportSession 硬件加速 | 上传 → FFmpeg 服务端处理 → 下载 |
| 裁剪精度 | 关键帧间隔（~1-2s） | 关键帧间隔（~1-2s） |
| 转码 | 不转码，直接读原文件 | 不转码，原文件上传到服务器 |

## Android 端（MVP-A 骨架）

Android 当前采用 Android-first MVP-A 骨架路线：先用 Kotlin + Jetpack Compose 建立可运行产品壳，模型层通过 `RallyProvider` 抽象接入，第一版只使用 deterministic `MockRallyProvider` 生成候选回合。

当前 Android 范围：

- `android/core`：纯 Kotlin rally contract、mock provider、回合审查状态流和单元测试。
- `android/app`：Compose 单 Activity，展示样例视频占位、提取回合、候选列表、状态统计、确认/删除/调整、转换片段草稿。
- 暂不接真实视频导入、播放、导出或真实模型。

后续真实模型或服务端分析只需要替换 `RallyProvider` 实现；审查 UI 和片段草稿转换逻辑不应绑定 mock provider。

## 未决问题

- 多角度视频关联是否需要在 MVP 阶段支持？
- Web 端是否需要 Docker Compose 一键部署脚本？
- CI/CD：iOS 端用 Xcode Cloud / GitHub Actions？Web 端用什么部署？
- 服务端 FFmpeg 的并发导出策略（同时最多几个任务）？
