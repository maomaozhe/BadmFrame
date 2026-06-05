# ADR 0004：基于球轨迹的回合切分

## 状态

提议

## 背景

ADR-0003 的启发式方案使用全局画面运动量、音频能量和状态机来剪掉死球时间。真实观看反馈显示效果很差、输出混乱。问题根源是信号层级错误：全局运动和音量无法稳定区分“正在打球”和“捡球、走动、调整、聊天、场边干扰”。

新的目标是：**每轮回合切得更准**。回合切分应优先围绕羽毛球本体信号，而不是整帧活跃程度。

调研要点：

- TrackNetV3 面向羽毛球等高速小目标追踪，包含轨迹预测和轨迹修正，目标是提升遮挡、背景干扰下的 shuttlecock tracking 稳定性。
- MonoTrack 将 court detection、player pose、shuttle tracking 和 badminton domain knowledge 组合起来做单目羽毛球轨迹重建，并提到用这些信号分割 shot sequence。
- 羽毛球落点/挑战系统实践也强调：需要结合 shuttle trajectory 与 court model / court lines 才能做可靠判断。
- 近期羽毛球动作/击球识别研究也普遍把 shuttle trajectory、player pose、court context 作为组合信号，而不是只看全局运动。

## 决策

下一版自动剪辑核心从“死球时间检测”改为：**基于球轨迹的半自动回合切分**。

第一版不追求完全自动导出最终剪辑，而是输出可审查的 rally candidates：

```text
video
-> main-court / activity-region estimation
-> TrackNetV3 shuttle trajectory
-> trajectory cleanup and continuity
-> velocity / direction / missing-span features
-> rally state machine
-> candidate rally clips
-> human review and correction
```

## 状态机

```text
Idle
  -> RallyActive
     when serve-like first hit, or enough continuous valid shuttle trajectory appears

RallyActive
  -> RallyActive
     while trajectory continues, or short occlusion / missed detections stay below tolerance

RallyActive
  -> RallyEndCandidate
     when trajectory indicates landing/net/out-of-play, or long no-shuttle span starts

RallyEndCandidate
  -> RallyActive
     if trajectory resumes quickly and continuity is plausible

RallyEndCandidate
  -> RallyEnd
     if no valid trajectory for long enough, shuttle drops near court/net, or player starts retrieval

RallyEnd
  -> Idle
     emit rally clip with pre/post buffers
```

## 核心信号

- `shuttle_visible`: TrackNetV3 是否检测到球。
- `shuttle_confidence`: 轨迹点置信度。
- `in_main_activity_region`: 球点是否落在主场地/主活动区域或合理扩展区域。
- `trajectory_gap`: 连续丢球时长。
- `velocity`: 球速，基于连续球点。
- `direction_change`: 速度方向变化，辅助识别击球事件。
- `trajectory_continuity`: 丢点前后轨迹是否可连接。
- `drop_or_net_candidate`: 轨迹向下停止、靠近地面/网附近、速度异常衰减等候选结束信号。
- `retrieval_signal`: 可选，球员离开击球区域、弯腰捡球或长期无击球轨迹。

## 产品形态

- 输出“候选回合”，不是直接覆盖原剪辑。
- 时间线显示 rally boundaries、轨迹可视化和置信度。
- 用户能快速确认、拆分、合并、修正边界。
- 用户修正结果进入评估集，用于后续调参或训练。

## 影响

- 需要引入模型运行环境，TrackNetV3 作为候选实现。
- 需要可靠 FFmpeg 解帧和模型推理管线。
- 需要主场地或主活动区域估计。产品主路径不要求用户手动框选 ROI；POC 可保留配置覆盖用于调试。
- 需要新增评估集和人工标注格式，否则无法判断算法是否改进。
- 前端需要支持轨迹/边界审查，而不是只显示粗糙 keep/cut 区间。

## 不做

- 不直接用全局运动量作为主判断。
- 不以“一键最终剪辑”为第一交付目标。
- 不在没有人工标注评估集的情况下继续调参。
- 不把 TrackNetV3 结果当作绝对真值；必须经过轨迹清洗和人工审查。

## 验收标准

第一阶段验收不是“剪掉多少秒”，而是：

- 能在 `video/140.mp4` 和至少一段多场地球馆视频上生成 shuttle trajectory JSON。
- 用户能在 UI 或调试输出中看到候选 rally boundaries。
- 对人工标注的回合，边界误差、漏检、误检和多场地背景误报可量化。
- 输出 candidates 足够稳定，可让用户在审查界面快速修正。

## 参考

- TrackNetV3: Enhancing ShuttleCock Tracking with Augmentations and Trajectory Rectification: https://github.com/qaz812345/TrackNetV3
- TrackNetV3 paper: https://people.cs.nycu.edu.tw/~yushuen/data/TrackNetV3.pdf
- MonoTrack: Shuttle trajectory reconstruction from monocular badminton video: https://openaccess.thecvf.com/content/CVPR2022W/CVSports/papers/Liu_MonoTrack_Shuttle_Trajectory_Reconstruction_From_Monocular_Badminton_Video_CVPRW_2022_paper.pdf
- Automatic Shuttlecock Fall Detection System: https://www.mdpi.com/1424-8220/22/21/8098
