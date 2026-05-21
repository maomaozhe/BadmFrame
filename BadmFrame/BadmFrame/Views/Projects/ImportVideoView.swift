import SwiftUI
import SwiftData
import PhotosUI
import UniformTypeIdentifiers

struct ImportVideoView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @State private var importPhase: ImportPhase = .selection
    @State private var selectedItem: PhotosPickerItem?
    @State private var projectName: String = ""
    @State private var metadata: VideoMetadata?
    @State private var copiedURL: URL?
    @State private var errorMessage: String?

    private let importService = VideoImportService()
    var onComplete: ((Project) -> Void)?

    enum ImportPhase {
        case selection
        case importing
        case metadataReview
    }

    var body: some View {
        NavigationStack {
            Group {
                switch importPhase {
                case .selection:
                    selectionView
                case .importing:
                    importingView
                case .metadataReview:
                    metadataReviewView
                }
            }
            .navigationTitle("导入视频")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
            }
        }
    }

    var selectionView: some View {
        VStack(spacing: 20) {
            Image(systemName: "video.badge.plus")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text("选择一段羽毛球视频")
                .font(.title2)

            PhotosPicker(selection: $selectedItem, matching: .videos) {
                Label("从相册选择", systemImage: "photo.on.rectangle")
            }
            .buttonStyle(.borderedProminent)
            .onChange(of: selectedItem) { _, item in
                guard let item else { return }
                processSelection(item)
            }
        }
    }

    var importingView: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text("正在导入...")
                .foregroundStyle(.secondary)
        }
    }

    var metadataReviewView: some View {
        Form {
            Section("项目名称") {
                TextField("名称", text: $projectName)
            }

            if let meta = metadata {
                Section("视频信息") {
                    LabeledContent("文件名", value: meta.fileName)
                    LabeledContent("时长", value: meta.durationSec.preciseDisplayString)
                    LabeledContent("分辨率", value: "\(meta.width)×\(meta.height)")
                    LabeledContent("帧率", value: String(format: "%.1f fps", meta.frameRate))
                    LabeledContent("编码", value: meta.codec)
                    if meta.isVFR {
                        LabeledContent("可变帧率") {
                            HStack {
                                Text("是")
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .foregroundColor(.yellow)
                            }
                        }
                    }
                }
            }

            Section {
                Button("创建项目") {
                    createProject()
                }
                .disabled(projectName.isEmpty)
            }
        }
    }

    func processSelection(_ item: PhotosPickerItem) {
        importPhase = .importing
        Task {
            do {
                let (meta, url) = try await importService.importVideo(from: item)
                metadata = meta
                copiedURL = url
                projectName = meta.fileName
                    .replacingOccurrences(of: ".\(url.pathExtension)", with: "")
                importPhase = .metadataReview
            } catch {
                errorMessage = error.localizedDescription
                importPhase = .selection
            }
        }
    }

    func createProject() {
        guard let meta = metadata, let url = copiedURL else { return }

        let project = Project(name: projectName)
        let video = SourceVideo(
            fileName: meta.fileName,
            filePath: url.path,
            durationSec: meta.durationSec,
            width: meta.width,
            height: meta.height,
            frameRate: meta.frameRate,
            codec: meta.codec,
            isVFR: meta.isVFR,
            fileSize: meta.fileSize
        )
        modelContext.insert(project)
        modelContext.insert(video)
        project.sourceVideo = video
        video.project = project
        try? modelContext.save()

        if let onComplete {
            onComplete(project)
        }
        dismiss()
    }
}
