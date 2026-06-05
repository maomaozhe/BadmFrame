# 自动剪掉死球时间

本文描述 BadmFrame 智能剪辑 MVP：导入视频后自动识别有效回合，剪掉下网后捡球、等待、走回发球位、聊天等死球时间。

## 当前状态

启发式方案已暂停。真实观看反馈显示：基于全局画面运动量、音频能量和状态机的自动剪辑效果很差，输出混乱，不能作为核心功能继续推进。

本文下面记录的是已试过的实验方案和失败经验，供后续设计避坑。后续需要重新分析问题定义、评估集和算法路线。

## 目标

- 减少用户从长视频里手动找回合的负担。
- 保留下网、失误和得分瞬间，但剪掉之后的长时间捡球和重置。
- 生成可编辑草稿，而不是不可逆自动剪辑。
- 优先支持固定机位、单场地、单段完整视频。

## 非目标

- 不直接承诺“自动识别精彩片段”。
- 不删除原视频。
- 不在第一版中依赖深度学习模型。
- 不解决多机位同步、自动计分、球路轨迹、击球类型识别。

## 用户流程

1. 用户导入一段羽毛球视频。
2. 点击“自动剪辑”或“自动去死球”。
3. 系统进入后台分析，显示进度。
4. 分析完成后，时间线上出现保留段和剪掉段。
5. 右侧列表展示自动候选片段、时间范围、置信度和简单理由。
6. 用户确认、恢复、删除或微调候选片段。
7. 用户导出拼接后的视频，或把候选片段保存到项目。

## 检测思路

按固定窗口分析视频，例如每 0.5 秒或 1 秒：

- `motion_score`：画面运动量，来自低频抽帧后的帧差。
- `audio_score`：音频能量和峰值密度，辅助识别击球、脚步、喊声。
- `play_score`：综合得分，用于判断当前窗口是否属于有效回合。

第一版用自适应阈值而不是固定数值。每个视频先计算分布，再用分位数区分低活动和高活动。

当前实现依赖可靠 FFmpeg：

- 灰度低分辨率抽帧，按窗口计算相邻帧差作为 `motion_score`。
- 单声道低采样率音频，按窗口计算 RMS 并归一化为 `audio_score`。
- 如果 FFmpeg 不可用或视频文件不存在，后端分析会明确失败，不生成伪结果。
- 状态机单元测试可以直接构造 `FeatureWindow`，不需要真实媒体文件。

本地如果没有 `ffmpeg`/`ffprobe` 在 `PATH` 中，可以通过环境变量指定：

```bash
BADMFRAME_FFMPEG_PATH=/opt/ffmpeg/bin/ffmpeg BADMFRAME_FFPROBE_PATH=/opt/ffmpeg/bin/ffprobe uvicorn app.main:app --reload
```

## 状态机

```text
idle
  -> candidate_play  连续高活动开始
  -> playing         高活动持续达到最小时长
  -> candidate_idle  低活动持续出现
  -> idle            低活动超过结束阈值，输出一个回合窗口
```

建议参数：

- 抽帧频率：3-5 fps。
- 分析窗口：0.5-1s。
- 进入回合：连续高活动 2-3s。
- 结束回合：连续低活动 3-5s。
- 片段缓冲：开始前 2s，结束后 3s。
- 合并间隔：小于 2s 的相邻片段合并。
- 最短片段：小于 4s 的候选片段丢弃。

## 下网和捡球

下网本身可能是用户想保留的失误瞬间，所以系统不应直接删除下网前后的整个事件。

策略：

- 保留下网前的回合和下网瞬间。
- 如果下网后进入低活动区间，则剪掉捡球、走位和等待。
- 下一个发球或回合开始前再接回。

## 后端设计

优先在 Web 后端实现，复用 Celery 和 FFmpeg：

```text
POST /api/v1/videos/{video_id}/analysis
GET  /api/v1/videos/{video_id}/analysis/{task_id}
POST /api/v1/projects/{project_id}/auto-clips/apply
POST /api/v1/exports              # body.merge=true 时按多个保留片段拼接成一个视频
```

内部模块建议：

```text
app/services/analysis.py
app/tasks/analysis.py
app/schemas/analysis.py
app/api/analysis.py
```

核心函数：

```text
extract_motion_features(video_path, crop?)
extract_audio_features(video_path)
detect_play_windows(features, params)
score_windows(windows, features)
create_auto_clip_draft(project_id, windows)
```

## 已实现的实验基线

- 后端提供分析 schema、service、task 和 API，并用 JSON 文件保存分析结果。
- `detect_play_windows` 实现了自适应阈值、状态机、缓冲、短间隔合并、过短片段过滤，并输出 `keep`/`cut` segment。
- `extract_motion_features` 使用 FFmpeg 做真实抽帧和音频能量提取；缺少 FFmpeg 时 API 明确报错。
- 前端提供本地模拟分析入口：显示分析状态、候选区间、时间线保留/剪掉覆盖层，并可应用为现有 clips。
- 这些实现仅作为实验基线，不代表产品可用方案。

## 数据形态

MVP 可以先把分析结果作为 JSON 存储，等行为稳定后再迁移到独立表。

```json
{
  "videoId": "uuid",
  "status": "completed",
  "params": {
    "mode": "balanced",
    "preBufferSec": 2,
    "postBufferSec": 3
  },
  "segments": [
    {
      "startSec": 12.4,
      "endSec": 28.8,
      "confidence": 0.82,
      "reason": ["high_motion", "audio_peaks"],
      "source": "auto",
      "state": "keep"
    }
  ]
}
```

## 前端设计

- 在导入后提供“自动剪辑”入口。
- 分析中展示任务进度。
- 时间线用不同颜色显示 `keep` 和 `cut` 区间。
- 候选列表支持确认、恢复、删除、调边界。
- 导出前展示预计保留时长和剪掉时长。
- 导出弹窗支持“导出合辑”，把选中片段按时间顺序录制为一个连续视频。

## 验收标准

- 固定机位 30-40 分钟视频能完成分析并生成候选片段。
- 明显捡球、等待、走位准备时间能被剪掉 60-80%。
- 主体回合不被整段误删。
- 用户能恢复误剪片段。
- 导出结果按确认后的保留片段拼接。

## 风险

- 手持视频、多人多场地、背景运动会干扰帧差。
- 球馆噪音会干扰音频峰值。
- 发球准备和慢节奏相持可能被误判为死球。
- 下网后短暂停顿可能让片段边界过早结束。
- 全局运动量无法理解“在打球”和“人在走动/捡球/调整机位”的语义差异。
- 输出结果即使数值上剪掉了一些时间，观看上仍可能非常混乱。

第一版需要把结果做成可编辑草稿，用用户确认兜底。
