# ADR 0002：技术架构决策

## 状态

已接受

## 背景

BadmFrame 完成文档脚手架（ADR-0001）后，需要选定技术架构以进入 MVP 实现。核心产品方向已确定：面向业余羽毛球爱好者的视频标记和裁剪工具，工作流为"导入 → 浏览 → 打标记 → 裁剪 → 导出 → 归档"。

## 决策

### 平台策略：iOS + Web 双平台，两端独立

- **iOS 端**：SwiftUI + AVFoundation + SwiftData，纯本地应用，零服务端依赖
- **Web 端**：React 19 + FastAPI + MySQL + Redis，前后端分离

两端独立运行，数据不同步。用户在哪个平台操作就在哪个平台完成全流程。

### iOS 端技术栈

| 决策 | 选择 | 理由 |
|------|------|------|
| UI 框架 | SwiftUI | Apple 官方、与 iOS 17+ 深度集成 |
| 数据持久化 | SwiftData | @Model 宏零样板、自动迁移、@Query 自动驱动 UI |
| 视频播放 | AVPlayer | 硬件解码 H.264/HEVC、VFR 自动处理、零额外开销 |
| 缩略图 | AVAssetImageGenerator | 系统原生、硬件加速 |
| 片段导出 | AVAssetExportSession | 硬件加速编码、支持 passthrough（不重编码） |
| 最低系统 | iOS 17 | 解锁 SwiftData + @Observable + 新版 SwiftUI API |

### Web 前端技术栈

| 决策 | 选择 | 理由 |
|------|------|------|
| UI 框架 | React 19 + TypeScript | 生态成熟、视频时间线 UI 参考实现丰富 |
| 状态管理 | Zustand | 轻量、sliceable、可从 React 外部订阅（IPC/WebSocket 回调友好） |
| 样式 | Tailwind CSS v4 | 原子化 CSS、@theme 定义 token、与 shadcn/ui 无缝配合 |
| 组件库 | shadcn/ui（Radix 无样式原语） | 可访问性内置、复制到项目内可完全自定义、轻量 |
| 构建 | Vite | HMR 快、Tailwind v4 插件原生支持 |
| 图标 | lucide-react | 与 shadcn/ui 默认配套 |

### Web 后端技术栈

| 决策 | 选择 | 理由 |
|------|------|------|
| Web 框架 | FastAPI | 异步原生、WebSocket 支持、自动 OpenAPI 文档 |
| 数据库 | MySQL 8.0 | 关系型数据（项目/标记/片段）天然适合 |
| ORM | SQLAlchemy 2.0 (async) | Python 生态标准、异步支持成熟 |
| 缓存/队列 | Redis | 导出任务队列、进度实时缓存、上传状态 |
| 任务队列 | Celery（Redis broker） | 异步导出任务、重试机制、进度回调 |
| 视频处理 | FFmpeg（subprocess） | 业界标准、格式支持全 |
| 文件存储 | 本地磁盘 + 定时清理 | MVP 阶段无需对象存储，定时清理过期文件即可 |
| 迁移工具 | Alembic | 与 SQLAlchemy 配套、版本化管理 |

### 视频处理策略

- **iOS**：不转码，AVPlayer 直读原文件。导出用 AVAssetExportSession passthrough（stream copy），精度受关键帧间隔限制（~1-2 秒）
- **Web**：视频上传到服务器，FFmpeg 处理。导出同样默认 stream copy

## 影响

- iOS MVP 可以独立开发、独立交付，不依赖后端
- Web 端需要前后端同时开发，但后端 API 设计完成后前后端可并行
- 两端数据模型概念对齐但独立存储，未来如需互通需额外设计同步方案
- 项目仓库将包含三个独立的代码目录：`BadmFrame/`（iOS）、`web/`、`server/`
- 文档（docs/）继续作为跨端的公共上下文

## 当前已确定内容

- iOS 零第三方依赖，全部使用 Apple 系统框架
- Web 前端不引入 React Router（仅有项目列表、编辑器两个视图）
- Web 后端视频处理为单任务队列（Celery），MVP 阶段不并发
- 两端数据模型字段对齐，方便未来迁移

## 未决问题

- Web 端是否需要 Docker Compose 一键部署？
- 服务端 FFmpeg 并发导出上限？
- CI/CD 方案？
- 是否需要用户系统（多用户隔离）还是单机使用？
