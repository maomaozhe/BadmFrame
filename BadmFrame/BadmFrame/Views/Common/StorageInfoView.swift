import SwiftUI

struct StorageInfoView: View {
    let usedBytes: Int64
    let availableBytes: Int64

    var body: some View {
        HStack {
            Text("已用")
            Spacer()
            Text(formatBytes(usedBytes))
                .foregroundStyle(.secondary)
            Text("可用")
            Text(formatBytes(availableBytes))
                .foregroundStyle(.secondary)
        }
    }

    func formatBytes(_ bytes: Int64) -> String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: bytes)
    }
}
