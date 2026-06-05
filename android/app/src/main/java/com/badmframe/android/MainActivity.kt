package com.badmframe.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.badmframe.core.rally.ClipDraft
import com.badmframe.core.rally.MockRallyProvider
import com.badmframe.core.rally.RallyAnalysisInput
import com.badmframe.core.rally.RallyCandidate
import com.badmframe.core.rally.RallyReviewState
import com.badmframe.core.rally.RallyReviewUiState
import com.badmframe.core.rally.RallyReviewViewModel
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    val viewModel = remember { RallyReviewViewModel(MockRallyProvider()) }
                    RallyReviewRoute(viewModel = viewModel)
                }
            }
        }
    }
}

@Composable
fun RallyReviewRoute(viewModel: RallyReviewViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    val scope = rememberCoroutineScope()

    RallyReviewScreen(
        uiState = uiState,
        onAnalyze = {
            scope.launch {
                viewModel.analyze(RallyAnalysisInput(videoId = "sample-local-video", durationSec = 96.0))
            }
        },
        onAccept = viewModel::acceptCandidate,
        onReject = viewModel::rejectCandidate,
        onAdjust = viewModel::adjustCandidate,
        onConvert = viewModel::convertAcceptedToClips,
    )
}

@Composable
fun RallyReviewScreen(
    uiState: RallyReviewUiState,
    onAnalyze: () -> Unit,
    onAccept: (String) -> Unit,
    onReject: (String) -> Unit,
    onAdjust: (String, Double, Double) -> Unit,
    onConvert: () -> Unit,
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            HeaderSection(isAnalyzing = uiState.isAnalyzing, onAnalyze = onAnalyze)
        }
        item {
            MediaPlaceholder()
        }
        item {
            SummarySection(uiState = uiState)
        }
        if (uiState.errorMessage != null) {
            item {
                Text(
                    text = uiState.errorMessage,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
        items(uiState.candidates, key = { it.id }) { candidate ->
            RallyCandidateCard(
                candidate = candidate,
                onAccept = onAccept,
                onReject = onReject,
                onAdjust = onAdjust,
            )
        }
        item {
            Button(
                onClick = onConvert,
                enabled = uiState.candidates.any {
                    it.reviewState == RallyReviewState.Accepted || it.reviewState == RallyReviewState.Adjusted
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("转换为片段")
            }
        }
        items(uiState.clips, key = { it.id }) { clip ->
            ClipDraftCard(clip = clip)
        }
    }
}

@Composable
private fun HeaderSection(isAnalyzing: Boolean, onAnalyze: () -> Unit) {
    Row(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.weight(1f)) {
            Text("BadmFrame Android MVP-A", style = MaterialTheme.typography.titleLarge)
            Text("样例视频 1:36", style = MaterialTheme.typography.bodyMedium)
        }
        Button(onClick = onAnalyze, enabled = !isAnalyzing) {
            Text(if (isAnalyzing) "提取中" else "提取回合")
        }
    }
}

@Composable
private fun MediaPlaceholder() {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("视频预览后续接入", fontWeight = FontWeight.SemiBold)
            Spacer(modifier = Modifier.height(4.dp))
            Text("本阶段只验证 mock 回合、快审状态和片段草稿。")
        }
    }
}

@Composable
private fun SummarySection(uiState: RallyReviewUiState) {
    val accepted = uiState.candidates.count { it.reviewState == RallyReviewState.Accepted }
    val rejected = uiState.candidates.count { it.reviewState == RallyReviewState.Rejected }
    val adjusted = uiState.candidates.count { it.reviewState == RallyReviewState.Adjusted }

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("候选回合摘要", fontWeight = FontWeight.SemiBold)
            Text("候选 ${uiState.candidates.size} · 已确认 $accepted · 已删除 $rejected · 已调整 $adjusted")
        }
    }
}

@Composable
private fun RallyCandidateCard(
    candidate: RallyCandidate,
    onAccept: (String) -> Unit,
    onReject: (String) -> Unit,
    onAdjust: (String, Double, Double) -> Unit,
) {
    var startText by remember(candidate.id, candidate.startSec) { mutableStateOf(candidate.startSec.toString()) }
    var endText by remember(candidate.id, candidate.endSec) { mutableStateOf(candidate.endSec.toString()) }

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(candidate.id, fontWeight = FontWeight.SemiBold)
            Text("${formatSeconds(candidate.startSec)} - ${formatSeconds(candidate.endSec)} · 置信度 ${candidate.confidence}")
            Text("状态：${candidate.reviewState.name} · 来源：${candidate.source.name}")
            Text("原因：${(candidate.startReason + candidate.endReason).distinct().joinToString(", ")}")

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = startText,
                    onValueChange = { startText = it },
                    label = { Text("开始") },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                )
                OutlinedTextField(
                    value = endText,
                    onValueChange = { endText = it },
                    label = { Text("结束") },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                )
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { onAccept(candidate.id) }) {
                    Text("确认")
                }
                OutlinedButton(onClick = { onReject(candidate.id) }) {
                    Text("删除")
                }
                Button(
                    onClick = {
                        val start = startText.toDoubleOrNull()
                        val end = endText.toDoubleOrNull()
                        if (start != null && end != null) {
                            onAdjust(candidate.id, start, end)
                        }
                    },
                ) {
                    Text("调整")
                }
            }
        }
    }
}

@Composable
private fun ClipDraftCard(clip: ClipDraft) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(clip.label, fontWeight = FontWeight.SemiBold)
            Text("${formatSeconds(clip.startSec)} - ${formatSeconds(clip.endSec)}")
            Text(clip.notes)
        }
    }
}

private fun formatSeconds(value: Double): String {
    val total = value.toInt()
    val minutes = total / 60
    val seconds = total % 60
    return "$minutes:${seconds.toString().padStart(2, '0')}"
}
