# Android-First MVP-A 实施记录

## 目标

Android 先实现可运行骨架，验证“mock 提取回合 -> 逐个快审 -> 转换片段草稿”的移动端产品形态。

## 范围

- 新建 `android/` Gradle 工程。
- `core` 模块承载纯 Kotlin 业务契约、mock provider、状态流和单元测试。
- `app` 模块承载 Kotlin + Jetpack Compose 单 Activity UI。
- 模型结果使用 deterministic `MockRallyProvider`。
- 不实现真实视频导入、播放、导出或真实模型调用。

## 核心契约

```kotlin
interface RallyProvider {
    suspend fun analyze(input: RallyAnalysisInput): List<RallyCandidate>
}
```

第一版实现：

```kotlin
class MockRallyProvider : RallyProvider
```

UI 和状态管理只依赖 `RallyProvider` 和 `RallyReviewViewModel`，后续真实模型、服务端分析或端上 runner 通过新增 provider 替换。

## 验收

- `MockRallyProvider` 根据时长返回稳定候选。
- 候选默认 `Pending`，时间范围合法，confidence 在 0 到 1。
- 用户能确认、删除、调整候选。
- accepted/adjusted 候选能转换为 `ClipDraft`。
- Compose 页面不展示虚假的真实视频能力，只显示明确占位。

## 后续

- 接入系统视频选择器。
- 接入 Media3 播放。
- 接入真实 `ServerRallyProvider` 或端上模型 provider。
- 增加导出能力和本地持久化。
