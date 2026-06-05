package com.badmframe.core.rally

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MockRallyProviderTest {
    private val provider = MockRallyProvider()

    @Test
    fun `analyze returns no candidates for zero duration`() = runTest {
        val candidates = provider.analyze(RallyAnalysisInput(videoId = "sample", durationSec = 0.0))

        assertEquals(emptyList<RallyCandidate>(), candidates)
    }

    @Test
    fun `analyze returns deterministic pending candidates within video duration`() = runTest {
        val input = RallyAnalysisInput(videoId = "sample", durationSec = 90.0)

        val first = provider.analyze(input)
        val second = provider.analyze(input)

        assertEquals(first, second)
        assertTrue(first.isNotEmpty())
        assertTrue(first.all { it.reviewState == RallyReviewState.Pending })
        assertTrue(first.all { it.source == RallySource.Mock })
        assertTrue(first.all { it.confidence in 0.0..1.0 })
        assertTrue(first.all { it.endSec > it.startSec })
        assertTrue(first.all { it.startSec >= 0.0 && it.endSec <= input.durationSec })
        assertEquals(first.sortedBy { it.startSec }, first)
    }

    @Test
    fun `analyze returns one bounded candidate for short positive duration`() = runTest {
        val candidates = provider.analyze(RallyAnalysisInput(videoId = "short", durationSec = 8.0))

        assertEquals(1, candidates.size)
        assertEquals(0.0, candidates.first().startSec, 0.001)
        assertEquals(8.0, candidates.first().endSec, 0.001)
    }
}
