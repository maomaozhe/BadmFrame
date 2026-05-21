import SwiftUI

struct ThumbnailStripView: View {
    let images: [Double: UIImage]
    let duration: Double
    let pixelsPerSecond: Double
    let scrollOffset: Double

    var body: some View {
        Canvas { context, size in
            for (seconds, image) in images {
                let x = (seconds * pixelsPerSecond) - scrollOffset
                guard x >= -60, x <= size.width + 60 else { continue }

                let rect = CGRect(x: x, y: 0, width: pixelsPerSecond, height: size.height)
                context.draw(Image(uiImage: image), in: rect)
            }
        }
    }
}
