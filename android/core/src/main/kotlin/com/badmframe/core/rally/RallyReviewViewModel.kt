package com.badmframe.core.rally

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class RallyReviewUiState(
    val isAnalyzing: Boolean = false,
    val candidates: List<RallyCandidate> = emptyList(),
    val selectedCandidateId: String? = null,
    val clips: List<ClipDraft> = emptyList(),
    val errorMessage: String? = null,
)

class RallyReviewViewModel(
    private val provider: RallyProvider,
) {
    private val _uiState = MutableStateFlow(RallyReviewUiState())
    val uiState: StateFlow<RallyReviewUiState> = _uiState.asStateFlow()

    suspend fun analyze(input: RallyAnalysisInput) {
        _uiState.value = _uiState.value.copy(isAnalyzing = true, errorMessage = null)
        runCatching { provider.analyze(input) }
            .onSuccess { candidates ->
                _uiState.value = RallyReviewUiState(
                    isAnalyzing = false,
                    candidates = candidates,
                    selectedCandidateId = candidates.firstOrNull()?.id,
                    clips = _uiState.value.clips,
                )
            }
            .onFailure { error ->
                _uiState.value = _uiState.value.copy(
                    isAnalyzing = false,
                    errorMessage = error.message ?: "回合提取失败",
                )
            }
    }

    fun selectCandidate(id: String) {
        if (_uiState.value.candidates.any { it.id == id }) {
            _uiState.value = _uiState.value.copy(selectedCandidateId = id)
        }
    }

    fun acceptCandidate(id: String) {
        updateCandidate(id) { it.copy(reviewState = RallyReviewState.Accepted) }
    }

    fun rejectCandidate(id: String) {
        updateCandidate(id) { it.copy(reviewState = RallyReviewState.Rejected) }
    }

    fun adjustCandidate(id: String, startSec: Double, endSec: Double) {
        if (startSec < 0.0 || endSec <= startSec) {
            _uiState.value = _uiState.value.copy(errorMessage = "起止时间无效")
            return
        }
        updateCandidate(id) {
            it.copy(
                startSec = startSec,
                endSec = endSec,
                reviewState = RallyReviewState.Adjusted,
            )
        }
    }

    fun convertAcceptedToClips() {
        val confirmed = _uiState.value.candidates
            .filter { it.reviewState == RallyReviewState.Accepted || it.reviewState == RallyReviewState.Adjusted }
            .sortedBy { it.startSec }

        val clips = confirmed.mapIndexed { index, candidate ->
            ClipDraft(
                id = "clip-${candidate.id}",
                startSec = candidate.startSec,
                endSec = candidate.endSec,
                label = "有效回合 ${index + 1}",
                notes = "source:rally-candidate confidence:${candidate.confidence}",
            )
        }

        _uiState.value = _uiState.value.copy(clips = clips, errorMessage = null)
    }

    private fun updateCandidate(id: String, transform: (RallyCandidate) -> RallyCandidate) {
        var found = false
        val candidates = _uiState.value.candidates.map { candidate ->
            if (candidate.id == id) {
                found = true
                transform(candidate)
            } else {
                candidate
            }
        }
        _uiState.value = _uiState.value.copy(
            candidates = candidates,
            selectedCandidateId = if (found) id else _uiState.value.selectedCandidateId,
            errorMessage = if (found) null else "候选回合不存在",
        )
    }
}
