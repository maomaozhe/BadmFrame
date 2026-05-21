import Foundation
import SwiftUI

@Observable
final class TimelineViewModel {
    var zoomLevel: Double = 1.0
    var pixelsPerSecond: Double = 10
    var scrollOffset: Double = 0

    var minimumPixelsPerSecond: Double = 2
    var maximumPixelsPerSecond: Double = 100

    func updateZoom(scale: Double) {
        zoomLevel = (zoomLevel * scale).clamped(to: 1.0...30.0)
        pixelsPerSecond = (10 * zoomLevel).clamped(to: minimumPixelsPerSecond...maximumPixelsPerSecond)
    }

    func timeAtPosition(x: CGFloat) -> Double {
        Double(x) / pixelsPerSecond
    }

    func positionForTime(_ seconds: Double) -> CGFloat {
        CGFloat(seconds * pixelsPerSecond)
    }

    func scrollToTime(_ seconds: Double, viewWidth: CGFloat) {
        let targetPosition = seconds * pixelsPerSecond
        scrollOffset = max(0, targetPosition - viewWidth / 2)
    }
}

extension Double {
    func clamped(to range: ClosedRange<Double>) -> Double {
        min(max(self, range.lowerBound), range.upperBound)
    }
}
