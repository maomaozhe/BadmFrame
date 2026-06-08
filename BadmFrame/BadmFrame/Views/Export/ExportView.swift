import SwiftUI

struct ExportView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    let project: Project
    let exportService: ExportService
    let clipVM: ClipViewModel

    @State private var selectedClipIDs: Set<String> = []
    @State private var isExporting = false
    @State private var exportComplete = false
    @State private var exportResults: [(clip: Clip, success: Bool, path: String?)] = []

    var body: some View {
        NavigationStack {
            Group {
                if exportComplete {
                    resultsView
                } else {
                    selectionView
                }
            }
            .navigationTitle("导出片段")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
            }
        }
    }

    var selectionView: some View {
        List {
            ForEach(project.clips.sorted(by: { $0.startTimeSec < $1.startTimeSec }), id: \.persistentModelID) { clip in
                HStack {
                    VStack(alignment: .leading) {
                        Text(clip.label.isEmpty ? "未命名片段" : clip.label)
                            .font(.subheadline)
                        Text("\(clip.startTimeDisplay) → \(clip.endTimeDisplay) (\(clip.durationDisplay))")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    if selectedClipIDs.contains(clipSelectionID(clip)) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundStyle(.blue)
                    }
                }
                .contentShape(Rectangle())
                .onTapGesture {
                    let id = clipSelectionID(clip)
                    if selectedClipIDs.contains(id) {
                        selectedClipIDs.remove(id)
                    } else {
                        selectedClipIDs.insert(id)
                    }
                }
            }
        }
        .safeAreaInset(edge: .bottom) {
            VStack(spacing: 8) {
                Button {
                    startExport(project.clips.sorted(by: { $0.startTimeSec < $1.startTimeSec }))
                } label: {
                    Text(isExporting ? "导出中..." : "一键导出全部片段")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(project.clips.isEmpty || isExporting)

                Button {
                    startBatchExport()
                } label: {
                    Text(isExporting ? "导出中..." : "导出 \(selectedClipIDs.count) 个片段")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .disabled(selectedClipIDs.isEmpty || isExporting)
            }
            .padding()
        }
    }

    var resultsView: some View {
        let successCount = exportResults.filter(\.success).count
        let failCount = exportResults.count - successCount

        return VStack(spacing: 16) {
            Image(systemName: failCount == 0 ? "checkmark.circle.fill" : "checkmark.circle")
                .font(.system(size: 48))
                .foregroundStyle(failCount == 0 ? .green : .orange)

            Text("导出完成")
                .font(.title2)
            Text("成功 \(successCount) 个\(failCount > 0 ? "，失败 \(failCount) 个" : "")")
                .foregroundStyle(.secondary)

            List {
                ForEach(exportResults, id: \.clip.persistentModelID) { result in
                    HStack {
                        Image(systemName: result.success ? "checkmark.circle.fill" : "xmark.circle.fill")
                            .foregroundStyle(result.success ? .green : .red)
                        Text(result.clip.label.isEmpty ? "未命名" : result.clip.label)
                        Spacer()
                        if let path = result.path {
                            Text(URL(fileURLWithPath: path).lastPathComponent)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .listStyle(.plain)

            Button("完成") { dismiss() }
                .buttonStyle(.borderedProminent)
        }
        .padding()
    }

    func startBatchExport() {
        let selected = project.clips.filter { selectedClipIDs.contains(clipSelectionID($0)) }
        startExport(selected)
    }

    func startExport(_ selected: [Clip]) {
        guard !selected.isEmpty else { return }
        isExporting = true
        Task {
            var results: [(clip: Clip, success: Bool, path: String?)] = []
            for clip in selected {
                guard let sourcePath = project.sourceVideo?.filePath else {
                    results.append((clip, false, nil))
                    continue
                }
                clipVM.updateExportStatus(clip, status: .exporting, context: modelContext)
                do {
                    let url = try await exportService.exportClip(
                        sourcePath: sourcePath,
                        startTime: clip.startTimeSec,
                        endTime: clip.endTimeSec,
                        outputName: "\(project.name)_\(Int(clip.startTimeSec))s-\(Int(clip.endTimeSec))s.mp4"
                    )
                    clipVM.updateExportStatus(clip, status: .completed, filePath: url.path, context: modelContext)
                    results.append((clip, true, url.path))
                } catch {
                    clipVM.updateExportStatus(clip, status: .failed, context: modelContext)
                    results.append((clip, false, nil))
                }
            }
            exportResults = results
            exportComplete = true
            isExporting = false
        }
    }

    private func clipSelectionID(_ clip: Clip) -> String {
        String(describing: clip.persistentModelID)
    }
}
