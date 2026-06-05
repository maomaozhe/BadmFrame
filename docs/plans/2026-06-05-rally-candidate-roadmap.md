# 有效回合候选路线实施计划

> **给开发 Agent：** 实施本计划时必须先使用 `superpowers:executing-plans`，按任务逐项执行、验证和提交。

**目标：** 实现 BadmFrame 路线 A：从羽毛球长视频中自动提取有效回合候选，用户在 Web 审查台快速确认、删除或微调边界，再把确认后的回合转成普通片段并复用现有导出流程。

**架构方向：** Web 是第一阶段用户可见的验证入口。模型/算法层通过标准 JSON 和 API 契约隔离，TrackNetV3、其他模型或离线推理都可以替换，不影响审查工作流。iOS/Android 仍是主产品方向，但移动端模型运行位置暂不在本计划内决定，等 Web 上候选质量和交互闭环验证后再定。

**技术栈：** FastAPI、SQLAlchemy、Pydantic、现有 FFmpeg/Celery 基线、React 19、TypeScript、Zustand、Playwright、pytest。

---

## 1. 产品决策

- 主路线：优先做“有效回合提取引擎”，不做通用剪辑器。
- 首发载体：Web 审查台。
- 第一版成功标准：大多数真实有效回合能被找到；边界允许前后多留 1-3 秒，但用户必须能很快微调。
- 默认审查方式：逐个快审，支持确认、删除、跳转播放、微调起止。
- 输出形态：确认或调整后的候选回合转成普通 clips，继续复用现有片段导出和合辑导出。
- 移动端模型位置：延后决策。本计划不假设最终一定云端化，但第一阶段允许使用服务端、桌面或外部 JSON 结果验证。

## 2. 数据契约

新增 rally candidate 契约，不继续扩展已暂停的 `AutoClipSegment` keep/cut 草稿模型。

前端类型：

```ts
export type RallyReviewState = "pending" | "accepted" | "rejected" | "adjusted";

export interface RallyCandidate {
  id: string;
  startSec: number;
  endSec: number;
  confidence: number;
  reviewState: RallyReviewState;
  startReason: string[];
  endReason: string[];
  source: "model" | "imported-json" | "manual";
  trajectoryStats?: {
    visibleRatio?: number;
    maxGapSec?: number;
    directionChanges?: number;
    meanSpeedPxSec?: number;
  };
}
```

后端响应：

```json
{
  "task_id": "uuid",
  "video_id": "uuid",
  "project_id": "uuid",
  "status": "completed",
  "progress": 1,
  "duration_sec": 120,
  "candidates": [
    {
      "id": "rally-001",
      "start_sec": 14,
      "end_sec": 21,
      "confidence": 0.82,
      "review_state": "pending",
      "start_reason": ["trajectory_active"],
      "end_reason": ["trajectory_missing"],
      "source": "imported-json",
      "trajectory_stats": {
        "visible_ratio": 0.7,
        "max_gap_sec": 0.4
      }
    }
  ],
  "error": null
}
```

第一阶段保留旧的自动分析代码作为实验对照，不删除、不作为主入口展示。

## 3. 并行工作流

以下工作可以并行推进：

- 评估和 JSON 工具：任务 1-3。
- 后端 rally API 和结果存储：任务 4-6。
- Web 审查台和状态管理：任务 7-10。
- E2E、文案和文档收口：任务 11-13。

依赖关系：

- Web 可以先用本地 mock 或导入 JSON 开发，不必等待模型和后端全部完成。
- 后端 API 不依赖 TrackNetV3 本地可运行；先支持标准 JSON 导入和保存。
- TrackNetV3 集成不是本计划的一部分，只做 runner 边界。

## 4. 任务拆分

### 任务 1：新增 Rally Candidate 类型

**文件：**

- 修改：`web/src/types.ts`
- 新建：`server/app/schemas/rally.py`
- 新建测试：`server/tests/test_rally_schemas.py`

**步骤：**

1. 先写后端 schema 测试，覆盖 pending 候选、confidence 范围、`end_sec > start_sec`。
2. 运行：

   ```bash
   cd server
   ./.venv/bin/pytest tests/test_rally_schemas.py -v
   ```

   预期：失败，因为 schema 还不存在。

3. 实现 `server/app/schemas/rally.py`：
   - `RallyReviewState`
   - `RallySource`
   - `TrajectoryStats`
   - `RallyCandidateRead`
   - `RallyAnalysisResultRead`
   - `RallyCandidateUpdate`
   - `RallyCandidatesApplyRequest`
   - `RallyCandidatesApplyResponse`
4. 在 `web/src/types.ts` 增加同名业务类型。保留旧 `AutoClipDraft` 类型，避免迁移期间破坏现有代码。
5. 验证：

   ```bash
   cd server
   ./.venv/bin/pytest tests/test_rally_schemas.py -v
   cd ../web
   npm run build
   ```

6. 提交建议：

   ```bash
   git add web/src/types.ts server/app/schemas/rally.py server/tests/test_rally_schemas.py
   git commit -m "feat: add rally candidate contract"
   ```

### 任务 2：新增人工标注评估工具

**文件：**

- 新建：`server/app/services/rally_evaluation.py`
- 新建测试：`server/tests/test_rally_evaluation.py`
- 读取：`assets/reference/rally_annotations_140.json`

**步骤：**

1. 先写失败测试，覆盖边界误差、漏检、误报、一个候选覆盖多个标注。
2. 实现纯函数：
   - `load_annotations(path: Path) -> list[RallyInterval]`
   - `evaluate_candidates(annotations, candidates, overlap_threshold=0.3) -> RallyEvaluation`
3. 评估指标至少包含：
   - `matched_rallies`
   - `missed_rallies`
   - `false_rallies`
   - `merged_rallies`
   - `mean_start_error_sec`
   - `mean_end_error_sec`
4. 增加测试确认 `assets/reference/rally_annotations_140.json` 中有 8 个回合。
5. 验证：

   ```bash
   cd server
   ./.venv/bin/pytest tests/test_rally_evaluation.py -v
   ```

### 任务 3：支持从 JSON 导入候选回合

**文件：**

- 新建：`server/app/services/rally_import.py`
- 新建测试：`server/tests/test_rally_import.py`

**步骤：**

1. 写导入测试，覆盖 JSON 解析、按开始时间排序、非法时间范围报错。
2. 支持输入格式：

   ```json
   {
     "video": "sample.mp4",
     "source": "imported-json",
     "candidates": [
       {
         "id": "rally-001",
         "startSec": 14,
         "endSec": 21,
         "confidence": 0.8,
         "startReason": ["manual_seed"],
         "endReason": ["manual_seed"]
       }
     ]
   }
   ```

3. 将 camelCase 输入标准化为后端 snake_case 字段。
4. 默认 `review_state = "pending"`，`source = "imported-json"`。
5. 验证：

   ```bash
   cd server
   ./.venv/bin/pytest tests/test_rally_import.py -v
   ```

### 任务 4：新增后端 Rally API

**文件：**

- 新建：`server/app/api/rallies.py`
- 修改：`server/app/main.py`
- 新建测试：`server/tests/test_rally_api.py`

**步骤：**

1. 写 API 测试：
   - `POST /api/v1/videos/{video_id}/rallies/import` 接受候选 JSON body，返回 completed 结果。
   - `GET /api/v1/videos/{video_id}/rallies/{task_id}` 返回已保存结果。
   - video 不存在返回 404。
   - candidate 时间范围非法返回 422。
2. 参考 `server/tests/test_analysis.py` 的 SQLite override 写法。
3. 实现路由：
   - `POST /api/v1/videos/{video_id}/rallies/import`
   - `GET /api/v1/videos/{video_id}/rallies/{task_id}`
4. V1 结果存为 JSON 文件：`settings.storage_dir / "rallies"`。暂不新增数据库迁移。
5. 在 `server/app/main.py` 注册 router。
6. 验证：

   ```bash
   cd server
   ./.venv/bin/pytest tests/test_rally_api.py -v
   ./.venv/bin/pytest tests/test_analysis.py -v
   ```

### 任务 5：确认后的候选回合转成 Clips

**文件：**

- 修改：`server/app/api/rallies.py`
- 修改测试：`server/tests/test_rally_api.py`
- 修改：`web/src/store/clipSlice.ts`

**步骤：**

1. 写后端测试：
   - `accepted` 和 `adjusted` 候选会创建 clips。
   - `rejected` 和 `pending` 默认不创建 clips。
   - clip label 为 `有效回合 1`、`有效回合 2`。
   - clip notes 包含 `source:rally-candidate` 和 confidence。
2. 新增路由：
   - `POST /api/v1/projects/{project_id}/rallies/apply`
3. 默认 body：
   - `task_id`
   - `include_pending = false`
   - `replace_existing_rally = false`
4. 在 `web/src/store/clipSlice.ts` 增加 `createClipsFromRallyCandidates(candidates)`。
5. 验证：

   ```bash
   cd server
   ./.venv/bin/pytest tests/test_rally_api.py -v
   cd ../web
   npm run build
   ```

### 任务 6：新增模型 Runner 边界

**文件：**

- 新建：`server/app/services/rally_runner.py`
- 新建测试：`server/tests/test_rally_runner.py`
- 修改：`docs/rally-segmentation.md`

**步骤：**

1. 写测试：
   - 设置 `BADMFRAME_RALLY_CANDIDATES_PATH` 时，runner 返回导入 JSON 的候选。
   - 未配置 runner source 时，明确失败。
2. 实现：
   - `run_rally_detection(video_path: Path, duration_sec: float) -> list[RallyCandidateRead]`
   - 如果环境变量指向 JSON 文件，则导入该文件。
   - 否则抛出 `RuntimeError("Rally detection runner is not configured")`。
3. 更新 `docs/rally-segmentation.md`：V1 使用导入 JSON 或外部 runner，TrackNetV3 集成后续单独做。
4. 验证：

   ```bash
   cd server
   ./.venv/bin/pytest tests/test_rally_runner.py -v
   ```

### 任务 7：Web 自动 Tab 改成回合审查状态

**文件：**

- 修改：`web/src/types.ts`
- 修改：`web/src/components/Editor/EditorView.tsx`
- 新建：`web/src/components/Rallies/RallyReviewPanel.tsx`
- 新建：`web/src/store/rallySlice.ts`

**步骤：**

1. 新增 Zustand 状态：
   - 当前状态。
   - candidates。
   - selected candidate id。
   - actions：`setCandidates`、`updateCandidate`、`acceptCandidate`、`rejectCandidate`、`selectCandidate`、`resetRallies`。
2. 将 tab 文案从 `自动` 改为 `回合`。
3. 将顶部按钮文案改为 `提取回合`。
4. 第一阶段前端可以生成确定性的本地 mock candidates，但类型必须是 `RallyCandidate`。
5. `RallyReviewPanel` 显示：
   - 状态摘要。
   - pending/accepted/rejected/adjusted 数量。
   - 当前候选时间范围和 confidence。
   - 确认、删除、跳转、播放按钮。
   - start/end 数字输入。
   - `转换为片段` 按钮。
6. 验证：

   ```bash
   cd web
   npm run build
   ```

### 任务 8：时间线显示候选回合边界

**文件：**

- 修改：`web/src/components/Timeline/TimelineView.tsx`
- 修改：`web/src/components/Editor/EditorView.tsx`

**步骤：**

1. 先阅读 `TimelineView.tsx`，保持现有 markers、clips、旧 overlay 行为不变。
2. 新增可选 props：

   ```ts
   rallyCandidates?: RallyCandidate[];
   selectedRallyId?: string | null;
   onSelectRally?: (id: string) => void;
   ```

3. 渲染规则：
   - `accepted` / `adjusted`：保留色。
   - `pending`：中性颜色。
   - `rejected`：弱化颜色。
   - selected：更明显描边或高亮。
4. 在 `EditorView` 中从 `rallySlice` 传入候选回合。
5. 验证：

   ```bash
   cd web
   npm run build
   ```

### 任务 9：逐个快审播放行为

**文件：**

- 修改：`web/src/store/videoSlice.ts`
- 修改：`web/src/components/Rallies/RallyReviewPanel.tsx`
- 修改：`web/src/components/Editor/VideoPlayer.tsx`

**步骤：**

1. 复用现有 video state，不创建第二套播放状态。
2. 如果缺少 seek action，就在 `videoSlice` 增加。
3. `跳转`：seek 到当前候选 `startSec`。
4. `播放回合`：seek 到 `startSec` 并播放。
5. 播放到 `endSec` 后暂停或退出预览状态。
6. 验证：

   ```bash
   cd web
   npm run build
   ```

### 任务 10：Web 接入 Rally API

**文件：**

- 新建或修改：`web/src/services/rallyApi.ts`
- 修改：`web/src/components/Rallies/RallyReviewPanel.tsx`
- 修改：`web/src/components/Editor/EditorView.tsx`

**步骤：**

1. 新增 service：
   - `importRallyCandidates(videoId, candidates)`
   - `getRallyResult(videoId, taskId)`
   - `applyRallies(projectId, taskId, options)`
2. 如果当前 Web 仍主要是本地 IndexedDB 工作流，保留一个集中 mock fallback。
3. `提取回合`：
   - 有 backend video id 且 API 配置存在时调用后端。
   - 否则使用确定性的本地 candidates。
   - 最终都写入 `rallySlice`。
4. `转换为片段`：
   - 有 backend task 时调用后端 apply。
   - 否则调用 `createClipsFromRallyCandidates`。
5. 验证：

   ```bash
   cd web
   npm run build
   cd ../server
   ./.venv/bin/pytest tests/test_rally_api.py -v
   ```

### 任务 11：新增 Web E2E

**文件：**

- 新建：`web/e2e/tests/11-rally-review.spec.ts`
- 如需要，修改：`web/e2e/helpers/index.ts`

**步骤：**

1. 编写 Playwright 场景：
   - 点击 `提取回合` 后进入 `回合` tab 并显示 candidates。
   - 确认和删除候选会更新数量。
   - 修改 start/end 后候选变成 `adjusted`。
   - accepted/adjusted candidates 转换成 clips。
   - 转换后导出按钮可用。
2. 运行：

   ```bash
   cd web
   npm run test:e2e -- 11-rally-review.spec.ts
   ```

   如果当前脚本不支持单文件过滤，运行：

   ```bash
   npm run test:e2e
   ```

### 任务 12：产品文案和旧自动路径整理

**文件：**

- 修改：`web/src/components/Editor/EditorView.tsx`
- 修改：`web/src/components/Rallies/RallyReviewPanel.tsx`
- 修改：`docs/product.md`
- 修改：`docs/video-pipeline.md`

**步骤：**

1. 使用这些产品词：
   - `提取回合`
   - `候选回合`
   - `逐个快审`
   - `确认片段`
   - `导出合辑`
2. 避免承诺：
   - `自动精彩球`
   - `一键最终成片`
   - `AI 精彩程度判断`
3. 文档中明确：第一阶段用户可见路径是“候选回合 + 快审”，旧 dead-time analysis 是暂停的实验基线。
4. 验证：

   ```bash
   cd web
   npm run build
   ```

### 任务 13：最终验证

**步骤：**

1. 后端全量测试：

   ```bash
   cd server
   ./.venv/bin/pytest
   ```

2. Web build 和 E2E：

   ```bash
   cd web
   npm run build
   npm run test:e2e
   ```

3. 检查变更：

   ```bash
   git status --short
   git diff --stat
   ```

## 5. 验收标准

- Web 用户可以触发 `提取回合` 并看到候选回合。
- 用户可以逐个审查候选，确认、删除、微调边界。
- 确认或调整后的候选能转成普通 clips。
- 现有单片段导出和合辑导出可以继续使用这些 clips。
- 后端有 rally candidate API，并支持独立于 TrackNetV3 的 JSON 导入路径。
- 评估工具可以用 `assets/reference/rally_annotations_140.json` 对候选结果做量化比较。
- 旧“自动剪掉死球时间”不再作为主产品入口。

## 6. 默认假设

- V1 迁移期间保留旧 analysis 代码。
- V1 rally 结果存为 JSON 文件，不做数据库表和迁移。
- 本计划不集成 TrackNetV3。
- 本计划不实现 iOS/Android 自动识别。
- 不提交大视频、模型权重、推理缓存或导出结果。
- 如果后端接入暂时阻塞，Web 审查工作流先用确定性的本地 rally candidates 完成，但保留 API service 边界。

## 7. 后续需要再确认的问题

- 模型最终跑在云端、用户电脑、局域网桌面助手，还是移动端本地。
- 第一批真实视频评估集需要覆盖哪些机位和球馆环境。
- 边界误差目标是否从“可微调”推进到“接近成片”。
- 是否需要在 V2 提供默认全选并直接导出“有效回合集锦”。
