import SwiftUI

struct MarkerPanel: View {
    let markers: [Marker]
    var playerVM: PlayerViewModel
    var onDelete: (Marker) -> Void
    var onUpdateLabel: (Marker, String) -> Void
    var onCreateClip: (Marker) -> Void

    var body: some View {
        if markers.isEmpty {
            EmptyStateView(
                icon: "pin.slash",
                title: "还没有标记点",
                subtitle: "播放视频时点击标记按钮添加标记"
            )
        } else {
            List {
                ForEach(markers.sorted(by: { $0.timestampSec < $1.timestampSec })) { marker in
                    MarkerRow(
                        marker: marker,
                        duration: playerVM.duration,
                        onTap: { playerVM.seek(to: marker.timestampSec) },
                        onDelete: { onDelete(marker) },
                        onUpdateLabel: { label in onUpdateLabel(marker, label) },
                        onCreateClip: { onCreateClip(marker) }
                    )
                }
            }
            .listStyle(.plain)
        }
    }
}
