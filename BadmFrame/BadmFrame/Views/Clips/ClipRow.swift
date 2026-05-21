import SwiftUI

struct ClipRow: View {
    let clip: Clip
    var playerVM: PlayerViewModel
    var onDelete: () -> Void
    var onExport: () -> Void

    @State private var showingDeleteConfirmation = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(clip.label.isEmpty ? "未命名片段" : clip.label)
                    .font(.subheadline)
                    .fontWeight(.medium)

                Spacer()

                statusBadge
            }

            HStack(spacing: 16) {
                Button {
                    playerVM.seek(to: clip.startTimeSec)
                } label: {
                    Text(clip.startTimeDisplay)
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.blue)
                }
                .buttonStyle(.borderless)

                Text("→")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Button {
                    playerVM.seek(to: clip.endTimeSec)
                } label: {
                    Text(clip.endTimeDisplay)
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.blue)
                }
                .buttonStyle(.borderless)

                Text("(\(clip.durationDisplay))")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Spacer()

                HStack(spacing: 8) {
                    if clip.exportStatus == .none {
                        Button(action: onExport) {
                            Image(systemName: "square.and.arrow.up")
                                .font(.caption)
                        }
                        .buttonStyle(.borderless)
                    }

                    Button(role: .destructive) {
                        showingDeleteConfirmation = true
                    } label: {
                        Image(systemName: "trash")
                            .font(.caption)
                    }
                    .buttonStyle(.borderless)
                    .confirmationDialog(
                        "确定删除此片段？",
                        isPresented: $showingDeleteConfirmation
                    ) {
                        Button("删除", role: .destructive, action: onDelete)
                        Button("取消", role: .cancel) {}
                    } message: {
                        Text("删除后无法恢复，已导出的文件将被同时删除")
                    }
                }
            }

            if !clip.notes.isEmpty {
                Text(clip.notes)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }

    @ViewBuilder
    var statusBadge: some View {
        switch clip.exportStatus {
        case .none:
            EmptyView()
        case .exporting:
            HStack(spacing: 4) {
                ProgressView()
                    .scaleEffect(0.6)
                Text("导出中")
                    .font(.caption2)
            }
            .foregroundStyle(.blue)
        case .completed:
            Text("已导出")
                .font(.caption2)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.green.opacity(0.15))
                .foregroundStyle(.green)
                .clipShape(Capsule())
        case .failed:
            Text("导出失败")
                .font(.caption2)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.red.opacity(0.15))
                .foregroundStyle(.red)
                .clipShape(Capsule())
        }
    }
}
