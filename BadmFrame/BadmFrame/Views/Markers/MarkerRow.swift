import SwiftUI

struct MarkerRow: View {
    let marker: Marker
    let duration: Double
    var onTap: () -> Void
    var onDelete: () -> Void
    var onUpdateLabel: (String) -> Void
    var onCreateClip: () -> Void

    @State private var isEditing = false
    @State private var editText: String = ""
    @State private var showingDeleteConfirmation = false

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                Circle()
                    .fill(marker.color)
                    .frame(width: 12, height: 12)

                VStack(alignment: .leading, spacing: 2) {
                    if isEditing {
                        TextField("标记名称", text: $editText, onCommit: {
                            onUpdateLabel(editText)
                            isEditing = false
                        })
                        .textFieldStyle(.roundedBorder)
                    } else {
                        Text(marker.label.isEmpty ? "未命名标记" : marker.label)
                            .font(.subheadline)
                            .foregroundStyle(.primary)
                    }

                    Text(marker.timestampDisplay)
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }

                Spacer()

                HStack(spacing: 8) {
                    Button {
                        isEditing = true
                        editText = marker.label
                    } label: {
                        Image(systemName: "pencil")
                            .font(.caption)
                    }
                    .buttonStyle(.borderless)

                    Button(action: onCreateClip) {
                        Image(systemName: "scissors")
                            .font(.caption)
                    }
                    .buttonStyle(.borderless)

                    Button(role: .destructive) {
                        showingDeleteConfirmation = true
                    } label: {
                        Image(systemName: "trash")
                            .font(.caption)
                    }
                    .buttonStyle(.borderless)
                    .confirmationDialog(
                        "确定删除此标记？",
                        isPresented: $showingDeleteConfirmation
                    ) {
                        Button("删除", role: .destructive, action: onDelete)
                        Button("取消", role: .cancel) {}
                    } message: {
                        Text("删除后无法恢复")
                    }
                }
            }
            .padding(.vertical, 4)
        }
    }
}
