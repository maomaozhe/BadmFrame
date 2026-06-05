package com.badmframe.core.rally

enum class RallyReviewState {
    Pending,
    Accepted,
    Rejected,
    Adjusted
}

enum class RallySource {
    Mock,
    Model,
    ImportedJson
}

data class RallyCandidate(
    val id: String,
    val startSec: Double,
    val endSec: Double,
    val confidence: Double,
    val reviewState: RallyReviewState,
    val source: RallySource,
    val startReason: List<String>,
    val endReason: List<String>,
)

data class ClipDraft(
    val id: String,
    val startSec: Double,
    val endSec: Double,
    val label: String,
    val notes: String,
)

data class RallyAnalysisInput(
    val videoId: String,
    val durationSec: Double,
)

interface RallyProvider {
    suspend fun analyze(input: RallyAnalysisInput): List<RallyCandidate>
}
