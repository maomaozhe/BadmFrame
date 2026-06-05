package com.badmframe.core.rally

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class RallyReviewViewModelTest {
    @Test
    fun `analyze populates candidates from provider`() = runTest {
        val viewModel = RallyReviewViewModel(provider = MockRallyProvider())

        viewModel.analyze(RallyAnalysisInput(videoId = "sample", durationSec = 60.0))

        assertTrue(viewModel.uiState.value.candidates.isNotEmpty())
        assertEquals(false, viewModel.uiState.value.isAnalyzing)
        assertEquals(null, viewModel.uiState.value.errorMessage)
    }

    @Test
    fun `accept reject and adjust update candidate review states`() = runTest {
        val viewModel = RallyReviewViewModel(provider = MockRallyProvider())
        viewModel.analyze(RallyAnalysisInput(videoId = "sample", durationSec = 60.0))
        val ids = viewModel.uiState.value.candidates.map { it.id }

        viewModel.acceptCandidate(ids[0])
        viewModel.rejectCandidate(ids[1])
        viewModel.adjustCandidate(ids[2], startSec = 30.0, endSec = 36.0)

        val candidates = viewModel.uiState.value.candidates.associateBy { it.id }
        assertEquals(RallyReviewState.Accepted, candidates.getValue(ids[0]).reviewState)
        assertEquals(RallyReviewState.Rejected, candidates.getValue(ids[1]).reviewState)
        assertEquals(RallyReviewState.Adjusted, candidates.getValue(ids[2]).reviewState)
        assertEquals(30.0, candidates.getValue(ids[2]).startSec, 0.001)
        assertEquals(36.0, candidates.getValue(ids[2]).endSec, 0.001)
    }

    @Test
    fun `invalid adjust keeps old candidate range and reports error`() = runTest {
        val viewModel = RallyReviewViewModel(provider = MockRallyProvider())
        viewModel.analyze(RallyAnalysisInput(videoId = "sample", durationSec = 60.0))
        val candidate = viewModel.uiState.value.candidates.first()

        viewModel.adjustCandidate(candidate.id, startSec = 20.0, endSec = 10.0)

        val updated = viewModel.uiState.value.candidates.first { it.id == candidate.id }
        assertEquals(candidate.startSec, updated.startSec, 0.001)
        assertEquals(candidate.endSec, updated.endSec, 0.001)
        assertNotNull(viewModel.uiState.value.errorMessage)
    }

    @Test
    fun `convert accepted and adjusted candidates to clips only`() = runTest {
        val viewModel = RallyReviewViewModel(provider = MockRallyProvider())
        viewModel.analyze(RallyAnalysisInput(videoId = "sample", durationSec = 60.0))
        val ids = viewModel.uiState.value.candidates.map { it.id }

        viewModel.acceptCandidate(ids[0])
        viewModel.rejectCandidate(ids[1])
        viewModel.adjustCandidate(ids[2], startSec = 30.0, endSec = 36.0)
        viewModel.convertAcceptedToClips()

        val clips = viewModel.uiState.value.clips
        assertEquals(2, clips.size)
        assertTrue(clips.all { it.notes.contains("source:rally-candidate") })
        assertEquals(listOf("有效回合 1", "有效回合 2"), clips.map { it.label })
    }
}
