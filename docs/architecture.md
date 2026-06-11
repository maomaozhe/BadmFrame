# 架构说明

BadmFrame 的架构由 [ADR-0002](decisions/0002-technical-architecture.md) 决定，本文档是架构的持续记录。

## 平台与总体架构

BadmFrame 当前由 iOS、Web 前端、Web 后端和独立模型层组成；后续主产品运行环境是移动端本地运行，Web 主要用于测通链路、评估算法和验证工作流。

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

- **iOS 端**：纯本地应用，AVFoundation 硬件加速处理视频，SwiftData 本地存储；后续应优先承载真实用户工作流。
- **Android 端**：当前是 MVP-A 骨架和移动端交互验证方向，后续与 iOS 一起承担移动端本地自动剪辑目标。
- **Web 端**：前后端分离，前端 React 在浏览器中播放/标记，后端 FastAPI 负责视频处理和持久化；定位为链路验证、算法评估和调试平台，不作为长期主产品依赖。
- **各端独立运行**，数据不同步，用户在哪端操作就在哪端完成全流程。

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

## 模型推理层

自动剪辑主路线不再依赖主后端内的全局运动量启发式方案。当前 `model/` 已作为独立 TrackNetV3 适配层，主后端通过标准 JSON 和子进程调用消费模型产物：

- 输入：源视频路径、抽帧配置、可选调试 ROI 配置。
- 输出：`shuttle_points.json`、`court_estimate.json`、`rally_candidates.json`。
- 运行环境：独立于 FastAPI venv；权重、视频和推理输出放在 `model/.local/`，不入库。
- 主后端负责持久化任务状态、候选回合和用户审查结果；`RallyJob` 记录历史，`content_sha256` 支持同视频去重。
- 产品主路径不要求用户手动画 ROI；需要自动估计主场地或主活动区域。
- 后续目标是把有效回合识别和剪辑流程迁移到移动端本地运行；Web/后端模型管线用于验证算法质量、数据契约和端到端流程。
- 自动候选回合的边界误差目标是小于 1s；达不到时必须保留用户确认和微调能力。

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
| GET | `/api/v1/videos/{video_id}/rallies/{task_id}` | 查询回合检测结果 |
| POST | `/api/v1/videos/{video_id}/rallies/import` | 导入外部候选回合 JSON |
| POST | `/api/v1/projects/{project_id}/rallies/apply` | 将已确认候选回合转为 clips |
| POST | `/api/v1/videos/{video_id}/analysis` | 启发式 AutoClip 实验分析入口 |
| GET | `/api/v1/videos/{video_id}/analysis/{task_id}` | 查询 AutoClip 实验分析结果 |
| GET | `/api/v1/projects/{project_id}/analysis` | 查询项目 AutoClip 实验分析历史 |
| GET | `/api/v1/projects/{project_id}/analysis/latest` | 查询项目最新 AutoClip 实验分析 |
| POST | `/api/v1/projects/{project_id}/auto-clips/apply` | 将 AutoClip 实验草稿应用为 clips |

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

Android 当前是 MVP-A 骨架和移动端交互验证方向，不与 iOS/Web 主线同等成熟。它用 Kotlin + Jetpack Compose 建立可运行产品壳，模型层通过 `RallyProvider` 抽象接入，第一版只使用 deterministic `MockRallyProvider` 生成候选回合。

当前 Android 范围：

- `android/core`：纯 Kotlin rally contract、mock provider、回合审查状态流和单元测试。
- `android/app`：Compose 单 Activity，展示样例视频占位、提取回合、候选列表、状态统计、确认/删除/调整、转换片段草稿。
- 暂不接真实视频导入、播放、导出或真实模型。

后续真实模型优先考虑移动端本地推理；服务端分析可以继续作为验证和调试路径。审查 UI 和片段草稿转换逻辑不应绑定 mock provider。

## 未决问题

- 多角度视频关联是否需要在 MVP 阶段支持？
- 移动端本地模型使用 Core ML、ONNX Runtime、TFLite 还是平台原生方案？
- Web 端是否需要 Docker Compose 一键部署脚本，还是保持验证工具定位？
- CI/CD：移动端用 Xcode Cloud / GitHub Actions / Android CI？Web 端只做验证环境还是需要部署？
- 服务端 FFmpeg 的并发导出策略（同时最多几个任务）？
