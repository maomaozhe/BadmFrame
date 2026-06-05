package com.badmframe.core.rally

import kotlin.math.min

class MockRallyProvider : RallyProvider {
    override suspend fun analyze(input: RallyAnalysisInput): List<RallyCandidate> {
        if (input.durationSec <= 0.0) return emptyList()
        if (input.durationSec <= SHORT_VIDEO_MAX_SEC) {
            return listOf(createCandidate(index = 1, startSec = 0.0, endSec = round(input.durationSec)))
        }

        val ranges = mutableListOf<Pair<Double, Double>>()
        var cursor = 6.0
        var index = 1
        while (cursor < input.durationSec && index <= MAX_CANDIDATES) {
            val rallyLength = 9.0 + (index % 3) * 3.0
            val start = cursor
            val end = min(input.durationSec, start + rallyLength)
            if (end - start >= MIN_RALLY_SEC) {
                ranges += round(start) to round(end)
            }
            cursor = end + 7.0
            index += 1
        }

        if (ranges.isEmpty()) {
            return listOf(createCandidate(index = 1, startSec = 0.0, endSec = round(input.durationSec)))
        }

        return ranges.mapIndexed { idx, (start, end) ->
            createCandidate(index = idx + 1, startSec = start, endSec = end)
        }
    }

    private fun createCandidate(index: Int, startSec: Double, endSec: Double): RallyCandidate {
        val confidence = 0.74 + ((index - 1) % 3) * 0.06
        return RallyCandidate(
            id = "mock-rally-${index.toString().padStart(3, '0')}",
            startSec = startSec,
            endSec = endSec,
            confidence = round(confidence),
            reviewState = RallyReviewState.Pending,
            source = RallySource.Mock,
            startReason = listOf("mock_candidate"),
            endReason = listOf("mock_candidate"),
        )
    }

    private fun round(value: Double): Double = kotlin.math.round(value * 100.0) / 100.0

    private companion object {
        const val SHORT_VIDEO_MAX_SEC = 10.0
        const val MIN_RALLY_SEC = 4.0
        const val MAX_CANDIDATES = 8
    }
}
