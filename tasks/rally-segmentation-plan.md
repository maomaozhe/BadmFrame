# 基于球轨迹的回合切分计划

目标：用 TrackNetV3 球轨迹 + 自动主场地/活动区域估计 + 轨迹连续性 + 球速/方向变化 + 状态机 + 人工审查，实现更准确的羽毛球回合切分。

## 原则

- 不继续调 ADR-0003 的全局运动量方案。
- 先做候选回合和人工审查，不直接做最终自动剪辑。
- 先建立人工标注评估集，再评估算法好坏。
- TrackNetV3 是球点来源，不是完整解决方案；必须有主场地估计、清洗、状态机和审查。
- 产品主路径不要求用户手动画 ROI；需要用自动估计和低置信度兜底处理未知用户视频。

## 阶段 0：标注评估基线

- [x] 定义 `rally_annotations.json` 格式。
- [x] 为 `video/140.mp4` 标注第一批真实回合。
- [x] 写评估脚本：输入人工标注和候选，输出边界误差、漏检、误检、合并、碎片化。
- [ ] 记录 ADR-0003 当前输出作为失败基线。

产出：

- `assets/reference/rally_annotations_140.json`
- `server/tests/fixtures/rally_candidates.example.json`
- `tools/evaluate_rallies.py`

运行方式：

```bash
python tools/evaluate_rallies.py \
  --annotations assets/reference/rally_annotations_140.json \
  --candidates server/tests/fixtures/rally_candidates.example.json
```

如需保存机器可读报告，追加 `--output reports/rally_eval_140.json`。

真实视频（如 `video/140.mp4`）只保存在本地，通过脚本参数或环境约定传入后续推理流程；仓库只提交小型 JSON、脚本、测试和文档，不提交大视频、模型权重、推理缓存或导出结果。

## 阶段 1：TrackNetV3 POC

- [ ] 确认 TrackNetV3 权重、许可证和运行环境。
- [ ] 模型作为独立推理器运行，主服务通过标准 JSON 输入/输出调用，不深度耦合 Python 环境。
- [ ] 输入 `video/140.mp4`，输出 `shuttle_points.json`。
- [ ] 记录推理耗时、丢点情况和明显误检。

产出：

- `docs/tracknetv3-setup.md`
- `server/app/services/shuttle_tracking.py` 或 `tools/run_tracknetv3.py`
- `storage/analysis/<task>/shuttle_points.json`

## 阶段 2：主场地估计与轨迹清洗

- [ ] 自动估计主场地或主活动区域。
- [ ] 支持调试用 ROI 配置覆盖，但不作为用户主流程。
- [ ] 实现区域过滤和区域外扩。
- [ ] 实现短 gap 保持 active。
- [ ] 实现速度异常跳点过滤。
- [ ] 实现低置信度点标记，不直接丢失全部上下文。

产出：

- `court_estimate.json`
- `cleaned_trajectory.json`
- 清洗前/后轨迹统计

## 阶段 3：Rally 状态机

- [ ] 实现 `Idle -> RallyActive -> RallyEndCandidate -> RallyEnd`。
- [ ] 输入清洗轨迹，输出 `rally_candidates.json`。
- [ ] 每个候选包含 `startReason`、`endReason`、`confidence`、`trajectoryStats`。
- [ ] 用阶段 0 的评估脚本对比人工标注。

参数初稿：

- `min_visible_frames_to_start`
- `gap_tolerance_sec`
- `end_tolerance_sec`
- `max_plausible_speed_px_sec`
- `min_rally_duration_sec`
- `pre_buffer_sec`
- `post_buffer_sec`

## 阶段 4：审查 UI

- [ ] 时间线显示 rally candidates。
- [ ] 显示候选置信度和原因。
- [ ] 支持确认、调整、拆分、合并、删除。
- [ ] 保存人工审查结果。
- [ ] 能导出已确认回合。

## 阶段 5：质量门槛

进入自动导出前必须满足：

- [ ] 人工标注集上主要回合召回优先，漏检率可接受。
- [ ] 候选边界误差可通过少量人工调整修正。
- [ ] 错误类型可解释，不是随机混乱。
- [ ] 用户审查比从零手动切片明显更快。
- [ ] 多场地球馆视频中，背景场地误报不压过主场地候选。

## 暂不做

- 不做完全自动最终剪辑。
- 不做自动计分。
- 不做多机位同步。
- 不训练自有模型，除非 TrackNetV3 POC 证明迁移效果不足且已有标注数据。
