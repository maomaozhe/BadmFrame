import SwiftUI

struct TimelineView: View {
    @Bindable var playerVM: PlayerViewModel
    @State private var timelineVM = TimelineViewModel()
    @State private var dragOffset: CGFloat?
    @State private var lastPinchScale: CGFloat = 1.0

    let markers: [Marker]
    var thumbnails: [Double: UIImage] = [:]
    @Binding var selectedColorName: String
    var onAddMarker: () -> Void

    var body: some View {
        VStack(spacing: 4) {
            HStack {
                Button {
                    onAddMarker()
                } label: {
                    Image(systemName: "pin.fill")
                        .font(.caption)
                }
                .buttonStyle(.bordered)

                Menu {
                    ForEach(Marker.availableColors, id: \.name) { colorInfo in
                        Button {
                            selectedColorName = colorInfo.name
                        } label: {
                            HStack {
                                Circle()
                                    .fill(colorForName(colorInfo.name))
                                    .frame(width: 12, height: 12)
                                Text(colorInfo.displayName)
                                if selectedColorName == colorInfo.name {
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                    }
                } label: {
                    Circle()
                        .fill(colorForName(selectedColorName))
                        .frame(width: 18, height: 18)
                        .overlay(
                            Circle()
                                .stroke(Color.secondary.opacity(0.3), lineWidth: 1)
                        )
                }

                HStack(spacing: 4) {
                    Button {
                        timelineVM.updateZoom(scale: 0.5)
                    } label: {
                        Image(systemName: "minus.magnifyingglass")
                    }
                    .buttonStyle(.borderless)

                    Button {
                        timelineVM.updateZoom(scale: 1.5)
                    } label: {
                        Image(systemName: "plus.magnifyingglass")
                    }
                    .buttonStyle(.borderless)
                }
                .font(.caption)

                Spacer()

                Text(playerVM.currentTime.preciseDisplayString)
                    .font(.caption.monospacedDigit())
            }
            .padding(.horizontal, 8)

            GeometryReader { geometry in
                let totalWidth = max(
                    playerVM.duration * timelineVM.pixelsPerSecond,
                    geometry.size.width
                )

                ScrollView(.horizontal, showsIndicators: true) {
                    ZStack(alignment: .leading) {
                        rulerView(totalWidth: totalWidth)
                            .frame(height: 16)
                            .offset(y: -10)

                        thumbnailStripView(totalWidth: totalWidth)
                            .frame(height: 40)
                            .offset(y: 10)

                        markerLayerView(totalWidth: totalWidth)
                            .frame(height: 60)

                        playheadView
                            .frame(width: 2, height: 60)
                            .offset(x: timelineVM.positionForTime(playerVM.currentTime))
                    }
                    .frame(width: totalWidth, height: geometry.size.height)
                    .contentShape(Rectangle())
                    .gesture(
                        DragGesture(minimumDistance: 5)
                            .onChanged { value in
                                let time = value.location.x / timelineVM.pixelsPerSecond
                                playerVM.seek(to: max(0, min(time, playerVM.duration)))
                            }
                    )
                }
                .simultaneousGesture(
                    MagnifyGesture()
                        .onChanged { value in
                            let delta = value.magnification / lastPinchScale
                            timelineVM.updateZoom(scale: delta)
                            lastPinchScale = value.magnification
                        }
                        .onEnded { _ in
                            lastPinchScale = 1.0
                        }
                )
            }
        }
        .frame(height: 80)
    }

    func rulerView(totalWidth: CGFloat) -> some View {
        let intervalSeconds = calculateInterval(pixelsPerSecond: timelineVM.pixelsPerSecond)

        return Canvas { context, size in
            guard playerVM.duration > 0 else { return }

            var seconds: Double = 0
            while seconds <= playerVM.duration {
                let x = seconds * timelineVM.pixelsPerSecond
                guard x >= 0, x <= size.width else { seconds += intervalSeconds; continue }

                let isMajor = Int(seconds) % max(Int(intervalSeconds * 2), 1) == 0
                let lineHeight: CGFloat = isMajor ? 12 : 6

                context.stroke(
                    Path { $0.move(to: CGPoint(x: x, y: 0)); $0.addLine(to: CGPoint(x: x, y: lineHeight)) },
                    with: .color(.secondary.opacity(0.5)),
                    lineWidth: isMajor ? 1 : 0.5
                )

                if isMajor {
                    let label = seconds.displayString
                    let text = Text(label).font(.system(size: 8))
                    let resolved = context.resolve(text)
                    context.draw(resolved, at: CGPoint(x: x, y: lineHeight + 6))
                }

                seconds += intervalSeconds
            }
        }
    }

    func thumbnailStripView(totalWidth: CGFloat) -> some View {
        ThumbnailStripView(
            images: thumbnails,
            duration: playerVM.duration,
            pixelsPerSecond: timelineVM.pixelsPerSecond,
            scrollOffset: 0
        )
    }

    func markerLayerView(totalWidth: CGFloat) -> some View {
        Canvas { context, size in
            for marker in markers {
                let x = marker.timestampSec * timelineVM.pixelsPerSecond
                guard x >= 0, x <= size.width else { continue }

                let diamond = Path { path in
                    path.move(to: CGPoint(x: x, y: 0))
                    path.addLine(to: CGPoint(x: x - 5, y: 8))
                    path.addLine(to: CGPoint(x: x, y: 14))
                    path.addLine(to: CGPoint(x: x + 5, y: 8))
                    path.closeSubpath()
                }
                context.fill(diamond, with: .color(marker.color))
            }
        }
    }

    var playheadView: some View {
        Rectangle()
            .fill(Color.red)
            .frame(width: 2)
    }

    func calculateInterval(pixelsPerSecond: Double) -> Double {
        if pixelsPerSecond >= 40 { return 1 }
        if pixelsPerSecond >= 15 { return 2 }
        if pixelsPerSecond >= 8 { return 5 }
        if pixelsPerSecond >= 4 { return 10 }
        if pixelsPerSecond >= 2 { return 30 }
        return 60
    }

    private func colorForName(_ name: String) -> Color {
        switch name {
        case "red": return .red
        case "blue": return .blue
        case "green": return .green
        case "orange": return .orange
        case "purple": return .purple
        default: return .yellow
        }
    }
}
