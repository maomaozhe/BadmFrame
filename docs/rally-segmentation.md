# 基于球轨迹的回合切分

本文定义 BadmFrame 下一版自动剪辑核心：基于 shuttle trajectory 切分羽毛球回合。该路线替代 ADR-0003 中效果不达标的全局运动量启发式方案。

## 目标

- 每轮回合切得更准。
- 每个有效回合的候选边界误差目标小于 1s。
- 先生成可审查的候选回合，而不是直接一键导出最终剪辑。
- 以球轨迹、自动主场地/活动区域估计、轨迹连续性、球速/方向变化和状态机作为核心信号。
- 用人工审查结果建立评估集，后续所有算法改动必须能量化比较。
- 后续主运行环境是移动端本地推理和本地剪辑；Web 管线用于测通链路、调参、评估和复现。

## 当前实现状态

- `model/` 已作为独立 TrackNetV3 适配层，官方 TrackNetV3 以 submodule 位于 `model/vendor/TrackNetV3`。
- `model/scripts/run_pipeline.py` 已串起 TrackNetV3 推理、CSV 转换、轨迹清理、窗口分割和 `rally_candidates.json` 输出；MVP 阶段可用 `--skip-tracknet` 接入已有 CSV 做 dry run。
- 当前最佳窗口参数存于 `model/scripts/best_params.json`：`merge_gap=1.0`、`vis=0.2`、`mot=220`、`spread=260`。在 `E:\badm-video\140.mp4` 前 250s 的最近评估中，TrackNet-only 结果达到 recall=1.0、precision=0.7619、avg startErr=0.612s、avg endErr=0.501s。
- `RallyRefiner` 已实现但未启用；局部重检测会降低召回率，当前不如直接调优窗口参数。
- Web 后端已有 `server/app/services/rally_detection.py` 子进程管线调用和 `server/app/tasks/rally_detection.py` Celery 任务；当前公开 `server/app/api/rallies.py` 路由以候选导入、结果查询和应用为主，启动/进度查询仍需和真实工作流复测对齐。
- `RallyJob` 表持久化任务状态，`content_sha256` 支持同视频去重；同视频重复提交会复用已完成或运行中的任务，避免重复跑 GPU 推理。
- 评估集仍很小，目前只有 `assets/reference/rally_annotations_140.json` 一份人工标注，参数可能过拟合。

## 总体流程

```text
输入视频
  -> TrackNetV3 推理或已有 CSV dry run
  -> 轨迹清理 / 窗口分割 / 状态机
  -> 候选回合
  -> 人工审查 / 修正
  -> 确认后的候选转成普通 clips
  -> 复用现有导出流程
```

历史 V1 先固定 rally candidate JSON/API 契约和 Web 审查闭环，并支持导入 deterministic mock JSON。当前已进入 TrackNetV3 管线接入阶段，但主后端仍只消费标准 JSON 结果，不把 PyTorch/TrackNetV3 环境塞进 FastAPI venv。后续移动端接入时应复用同一候选回合契约和评估指标，避免 Web 验证链路和移动端实现分叉。

## 数据结构

### Shuttle Point

```json
{
  "frameIndex": 1234,
  "timeSec": 41.13,
  "x": 512.4,
  "y": 218.7,
  "confidence": 0.91,
  "visible": true,
  "source": "tracknetv3"
}
```

### Rally Candidate

```json
{
  "id": "rally-001",
  "startSec": 18.4,
  "endSec": 31.8,
  "confidence": 0.78,
  "startReason": ["continuous_trajectory", "serve_or_first_hit"],
  "endReason": ["long_missing_trajectory", "drop_candidate"],
  "reviewState": "pending",
  "trajectoryStats": {
    "visibleRatio": 0.72,
    "maxGapSec": 0.42,
    "directionChanges": 8,
    "meanSpeedPxSec": 920
  }
}
```

### Human Review

```json
{
  "candidateId": "rally-001",
  "action": "adjust",
  "startSec": 17.9,
  "endSec": 32.6,
  "comment": "end was cut before shuttle hit floor"
}
```

## 关键模块

### 1. 主场地估计

产品目标不要求用户手动框选球场。第一版应自动估计主场地或主活动区域，并把结果作为后续 TrackNet 点过滤和候选置信度的一部分。

优先级：

- 默认自动估计主场地或主活动区域。
- 多场地误检时降低候选置信度，但不打断用户流程。
- 输出可调试的 `courtEstimate`，用于评估和后续 UI 展示。
- POC 阶段可以允许配置文件覆盖 ROI，但不能把手动画框作为产品主路径。

可选实现信号：

- 首帧或抽样帧的球场线/地板区域。
- 人物和球点长期活动密度。
- TrackNet 初始球点聚类。
- 与人工标注回合重合度最高的候选区域。

### 2. 模型 runner 边界

TrackNetV3 不在 FastAPI 主进程内运行。后端只依赖稳定边界：

- 输入：源视频路径和视频时长。
- 输出：标准 rally candidate JSON。
- 本地验证：可跳过 TrackNetV3 推理，用已有 CSV 或 deterministic mock JSON 接入。
- 未配置可用 runner 或输入产物时必须明确失败，避免把空结果伪装成模型输出。

### 3. TrackNetV3 推理

目标输出每帧球点、可见性和置信度。

要求：

- 模型环境独立于主 FastAPI 进程，优先作为离线 worker 或 CLI。
- 推理结果写 JSON，便于复现、调试和重新跑状态机。
- 低置信度点不直接丢弃，进入轨迹清洗阶段。

### 4. 轨迹清洗

处理 TrackNet 常见问题：

- 短时间丢球：插值或保持 active。
- 背景误检：用主场地估计、速度上限、轨迹平滑过滤。
- 多场地干扰：优先保留主活动区域内或与上一轨迹连续的点。
- 突然跳点：如果速度不合理且无法连接，标记为 outlier。

### 5. 轨迹特征

按时间窗口计算：

- 可见点比例。
- 最大连续丢球时长。
- 速度均值/峰值。
- 方向变化次数。
- 轨迹是否靠近网/地面/边线候选区域。
- 轨迹是否从静止/低速进入高速。

### 6. Rally 状态机

```text
Idle
  -> RallyActive
     条件：连续有效球轨迹达到 N 帧，或出现 serve/first-hit 候选。

RallyActive
  -> RallyActive
     条件：球轨迹连续，或短暂丢球时间小于 gap_tolerance。

RallyActive
  -> RallyEndCandidate
     条件：长时间无球、轨迹停止、落点/下网候选、明显离开主活动区域。

RallyEndCandidate
  -> RallyActive
     条件：球轨迹很快恢复且与之前轨迹连续。

RallyEndCandidate
  -> RallyEnd
     条件：无球持续超过 end_tolerance，或出现捡球/重置候选。

RallyEnd
  -> Idle
     输出带 pre/post buffer 的候选回合。
```

## 评估方法

先建立小评估集，而不是继续凭观看感觉调参。

建议从 `video/140.mp4` 开始：

- 人工标注 10-20 个真实回合边界。
- 每个边界记录 `startSec`、`endSec`、是否完整、备注。
- 算法输出和人工标注比较：
  - `boundary_error_start`
  - `boundary_error_end`
  - `missed_rallies`
  - `false_rallies`
  - `fragmented_rallies`
  - `merged_rallies`

第一阶段成功标准：

- 召回优先：主要回合尽量不漏。
- 候选边界误差目标小于 1s；早期可通过用户微调兜底，但算法调优必须围绕该指标收敛。
- 误切原因可解释到轨迹缺失、误检、主场地估计错误或状态机阈值。
- 多场地球馆视频中，背景场地误报可存在，但不能压过主场地有效回合。

## 实施阶段

### 阶段 0：标注和评估

- 创建 rally 标注 JSON 格式。
- 在 `video/140.mp4` 上人工标注第一批回合。
- 写评估脚本，比较候选和人工标注。

### 阶段 1：候选 JSON / 外部 runner 边界（已完成）

- 固定 rally candidate JSON 契约和 API 存取路径。
- 支持 deterministic mock JSON 导入。
- 后端 runner 只定义边界，未配置时明确失败。
- Web 审查台可以先消费 mock candidates，不等待真实模型环境。

### 阶段 2：TrackNetV3 离线 POC（已接入）

- 以外部模型/CLI 方式跑 TrackNetV3。
- 输入视频或抽帧目录，输出 shuttle points JSON 或 rally candidate JSON。
- 不作为主 FastAPI 服务本地可运行前提。

### 阶段 3：主场地估计和轨迹清洗（部分完成）

- 自动估计主场地或主活动区域。
- 支持调试用 ROI 配置覆盖，但不作为用户主流程。
- 实现区域过滤、短 gap 保持、跳点过滤、简单插值。
- 输出清洗前/后的轨迹调试文件。

### 阶段 4：Rally 状态机（已接入基础版本）

- 基于轨迹特征输出候选 rally clips。
- 每个候选保留 reason 和 stats。
- 跑评估脚本，记录结果。

### 阶段 5：人工审查 UI

- 时间线显示候选回合边界。
- 可视化球轨迹和丢点区间。
- 支持确认、调整、合并、拆分、删除候选。
- 保存人工修正结果。

### 阶段 6：再考虑自动导出

- 当评估集上候选足够稳定后，再把确认后的 rally clips 接入导出。
- 未确认候选不直接进入最终剪辑。

### 阶段 7：移动端本地化

- 将已验证的候选回合契约、评估指标和状态机迁移到移动端本地运行。
- 评估 Core ML、ONNX Runtime、TFLite 或平台原生实现，重点关注耗时、包体、硬件要求和离线可用性。
- 移动端仍保留用户确认和边界微调；只有当评估集稳定达到 <1s 误差后，才考虑减少人工确认成本。

## 风险

- TrackNetV3 模型权重、环境和许可证仍需在交付/分发前确认清楚。
- 业余视频可能是手机竖屏、远景、多场地、遮挡严重。
- 球轨迹会频繁丢失，必须允许短 gap。
- 下网/落地不一定能单靠 2D 轨迹可靠判断，需要人工审查兜底。
- 自动主场地估计不可靠时，候选置信度和错误原因必须可见，避免伪装成确定结果。

## 参考

- TrackNetV3 GitHub: https://github.com/qaz812345/TrackNetV3
- TrackNetV3 paper: https://people.cs.nycu.edu.tw/~yushuen/data/TrackNetV3.pdf
- MonoTrack paper: https://openaccess.thecvf.com/content/CVPR2022W/CVSports/papers/Liu_MonoTrack_Shuttle_Trajectory_Reconstruction_From_Monocular_Badminton_Video_CVPRW_2022_paper.pdf
- Shuttlecock fall detection / court model: https://www.mdpi.com/1424-8220/22/21/8098
