import SwiftUI
import SwiftData

struct EditorView: View {
    @Environment(\.modelContext) private var modelContext
    @State private var playerVM = PlayerViewModel()
    @State private var markerVM = MarkerViewModel()
    @State private var clipVM = ClipViewModel()
    @State private var exportService = ExportService()
    @State private var thumbnailService = ThumbnailService()
    @State private var thumbnailImages: [Double: UIImage] = [:]
    @State private var selectedTab: EditorTab = .markers
    @State private var showingExport = false
    @State private var defaultMarkerColor: String = "yellow"
    let project: Project

    enum EditorTab: String, CaseIterable {
        case markers = "标记"
        case clips = "片段"
        case info = "信息"
    }

    var body: some View {
        VStack(spacing: 0) {
            VideoPlayerView(viewModel: playerVM)

            Divider()

            TimelineView(
                playerVM: playerVM,
                markers: project.markers,
                thumbnails: thumbnailImages,
                selectedColorName: $defaultMarkerColor,
                onAddMarker: { addMarker() }
            )

            Divider()

            HStack {
                Picker("面板", selection: $selectedTab) {
                    ForEach(EditorTab.allCases, id: \.self) { tab in
                        Text(tab.rawValue).tag(tab)
                    }
                }
                .pickerStyle(.segmented)
                .labelsHidden()

                Spacer()

                Button {
                    showingExport = true
                } label: {
                    Label("导出", systemImage: "square.and.arrow.up")
                }
                .buttonStyle(.bordered)
                .disabled(project.clips.isEmpty)
            }
            .padding(.horizontal)
            .padding(.vertical, 8)

            tabContent
                .frame(minHeight: 150)
        }
        .navigationTitle(project.name)
        .onAppear {
            if let path = project.sourceVideo?.filePath {
                playerVM.loadVideo(url: URL(fileURLWithPath: path))
            }
        }
        .onDisappear {
            playerVM.cleanup()
            thumbnailService.invalidate()
        }
        .onChange(of: playerVM.duration) { _, newDuration in
            guard newDuration > 0,
                  let path = project.sourceVideo?.filePath else { return }
            thumbnailService.configure(
                for: URL(fileURLWithPath: path),
                duration: newDuration
            )
            Task { @MainActor in
                thumbnailImages = await thumbnailService.generateThumbnails(interval: 1.0)
            }
        }
        .onKeyPress(.space) {
            playerVM.togglePlayPause()
            return .handled
        }
        .onKeyPress(characters: .alphanumerics) { keyPress in
            if keyPress.characters.lowercased() == "m" {
                addMarker()
                return .handled
            }
            return .ignored
        }
        .sheet(isPresented: $showingExport) {
            ExportView(
                project: project,
                exportService: exportService,
                clipVM: clipVM
            )
        }
    }

    @ViewBuilder
    var tabContent: some View {
        switch selectedTab {
        case .markers:
            MarkerPanel(
                markers: project.markers,
                playerVM: playerVM,
                onDelete: { deleteMarker($0) },
                onUpdateLabel: { marker, label in
                    markerVM.updateMarkerLabel(marker, label: label, context: modelContext)
                },
                onCreateClip: { marker in
                    createClipFromMarker(marker)
                }
            )
        case .clips:
            ClipPanel(
                clips: project.clips,
                playerVM: playerVM,
                onDelete: { deleteClip($0) },
                onExport: { clip in
                    exportSingleClip(clip)
                }
            )
        case .info:
            InfoPanel(project: project)
        }
    }

    func addMarker() {
        let time = playerVM.currentTime
        _ = markerVM.addMarker(at: time, colorName: defaultMarkerColor, project: project, context: modelContext)
    }

    func deleteMarker(_ marker: Marker) {
        markerVM.deleteMarker(marker, from: project, context: modelContext)
    }

    func createClipFromMarker(_ marker: Marker) {
        let start = max(0, marker.timestampSec - 3)
        let end = min(project.sourceVideo?.durationSec ?? 0, marker.timestampSec + 7)
        _ = clipVM.createClip(
            startTime: start,
            endTime: end,
            label: marker.label.isEmpty ? "片段" : marker.label,
            anchorMarkerId: String(describing: marker.persistentModelID),
            project: project,
            context: modelContext
        )
        selectedTab = .clips
    }

    func deleteClip(_ clip: Clip) {
        clipVM.deleteClip(clip, from: project, context: modelContext)
    }

    func exportSingleClip(_ clip: Clip) {
        guard let sourcePath = project.sourceVideo?.filePath else { return }
        Task {
            clipVM.updateExportStatus(clip, status: .exporting, context: modelContext)
            do {
                let outputURL = try await exportService.exportClip(
                    sourcePath: sourcePath,
                    startTime: clip.startTimeSec,
                    endTime: clip.endTimeSec,
                    outputName: "\(project.name)_\(Int(clip.startTimeSec))s-\(Int(clip.endTimeSec))s.mp4"
                )
                clipVM.updateExportStatus(clip, status: .completed, filePath: outputURL.path, context: modelContext)
            } catch {
                clipVM.updateExportStatus(clip, status: .failed, context: modelContext)
            }
        }
    }
}

struct InfoPanel: View {
    let project: Project
    @State private var storageInfo: (used: Int64, available: Int64)?

    private let importService = VideoImportService()

    var body: some View {
        List {
            if let video = project.sourceVideo {
                Section("源视频") {
                    LabeledContent("文件名", value: video.fileName)
                    LabeledContent("时长", value: video.durationSec.preciseDisplayString)
                    LabeledContent("分辨率", value: video.resolutionDisplay)
                    LabeledContent("帧率", value: video.frameRateDisplay)
                    LabeledContent("编码", value: video.codec)
                    if video.isVFR {
                        LabeledContent("可变帧率") {
                            HStack {
                                Text("是")
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .foregroundColor(.yellow)
                            }
                        }
                    }
                }

                Section("项目信息") {
                    LabeledContent("标记数量", value: "\(project.markerCount)")
                    LabeledContent("片段数量", value: "\(project.clipCount)")
                    LabeledContent("创建时间", value: project.createdAtDisplay)
                }

                if let info = storageInfo {
                    Section("存储空间") {
                        StorageInfoView(usedBytes: info.used, availableBytes: info.available)
                    }
                }
            }
        }
        .onAppear {
            storageInfo = importService.storageInfo()
        }
    }
}
