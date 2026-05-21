import SwiftUI

struct ClipPanel: View {
    let clips: [Clip]
    var playerVM: PlayerViewModel
    var onDelete: (Clip) -> Void
    var onExport: (Clip) -> Void

    var body: some View {
        if clips.isEmpty {
            EmptyStateView(
                icon: "scissors",
                title: "还没有片段",
                subtitle: "从标记点创建片段，或手动选择起止时间"
            )
        } else {
            List {
                ForEach(clips.sorted(by: { $0.startTimeSec < $1.startTimeSec })) { clip in
                    ClipRow(
                        clip: clip,
                        playerVM: playerVM,
                        onDelete: { onDelete(clip) },
                        onExport: { onExport(clip) }
                    )
                }
            }
            .listStyle(.plain)
        }
    }
}
