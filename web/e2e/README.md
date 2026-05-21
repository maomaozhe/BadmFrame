# BadmFrame Web E2E Tests

基于 Playwright 的端到端测试，覆盖 BadmFrame Web 前端的核心功能。

## 环境准备

```bash
# 安装依赖（在 web/ 目录）
cd web && npm install

# 安装 Playwright 浏览器（仅需一次）
npx playwright install chromium

# 生成测试视频 fixture（需要 ffmpeg）
# 如果没有 ffmpeg，可下载静态二进制：
# curl -L -o /tmp/ffmpeg.zip https://evermeet.cx/ffmpeg/ffmpeg-7.0.2.zip
# unzip /tmp/ffmpeg.zip -d /tmp && chmod +x /tmp/ffmpeg
/tmp/ffmpeg -f lavfi -i testsrc=duration=5:size=640x360:rate=30 \
  -f lavfi -i sine=frequency=440:duration=5 \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest -y \
  e2e/fixtures/test-video-5s.mp4
```

## 运行测试

```bash
cd web

# 全量运行（headless）
npm run test:e2e

# Playwright UI 模式
npm run test:e2e:ui

# 显示浏览器窗口
npm run test:e2e:headed

# 单步调试
npm run test:e2e:debug

# 运行单个测试文件
npx playwright test --config ../e2e/playwright.config.ts ../e2e/tests/01-project-list.spec.ts

# 按名称匹配
npx playwright test --config ../e2e/playwright.config.ts --grep "TC-PL"
```

## 查看结果

```bash
# Playwright HTML 报告
npm run test:e2e:report

# 截图预览页（每次运行自动生成）
open ../e2e/screenshots/<时间戳>/_index.html
```

## 目录结构

```
e2e/
├── playwright.config.ts    # Playwright 配置
├── fixtures/               # 测试用视频文件
├── helpers/                # 公共辅助函数
│   ├── db.ts               # IndexedDB 操作
│   ├── navigation.ts       # 页面导航断言
│   ├── project.ts          # 项目创建快捷操作
│   ├── marker.ts           # 标记操作
│   └── screenshots.ts      # 截图工具
├── tests/                  # 测试用例
│   ├── 01-project-list.spec.ts
│   ├── 02-import-video.spec.ts
│   ├── 03-editor-navigation.spec.ts
│   ├── 04-video-playback.spec.ts
│   ├── 05-timeline.spec.ts
│   ├── 06-markers.spec.ts
│   ├── 07-clips.spec.ts
│   ├── 08-export.spec.ts
│   └── 09-keyboard-shortcuts.spec.ts
├── screenshots/            # 截图输出（gitignored）
└── reports/                # HTML 报告（gitignored）
```

## 测试约定

- **命名**: `TC-XXNN: 描述` 格式（XX = 功能缩写，NN = 序号）
- **隔离**: 每个 test 前清空 IndexedDB，串行执行
- **截图**: 页面跳转、对话框开/关、空状态、状态变更等关键交互点自动截图
- **浏览器**: 仅 Chromium（依赖 IndexedDB + MediaRecorder）
