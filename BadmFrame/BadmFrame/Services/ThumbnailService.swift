import AVFoundation
import UIKit

@Observable
final class ThumbnailService {
    private var generator: AVAssetImageGenerator?
    private var thumbnailCache: [Int: UIImage] = [:]
    private var assetURL: URL?
    private var assetDuration: Double = 0

    func configure(for url: URL, duration: Double) {
        guard url != assetURL else { return }
        assetURL = url
        assetDuration = duration
        thumbnailCache.removeAll()

        let asset = AVAsset(url: url)
        let generator = AVAssetImageGenerator(asset: asset)
        generator.appliesPreferredTrackTransform = true
        generator.maximumSize = CGSize(width: 120, height: 68)
        generator.requestedTimeToleranceBefore = .zero
        generator.requestedTimeToleranceAfter = .zero
        self.generator = generator
    }

    func thumbnail(at seconds: Double) async -> UIImage? {
        guard let generator else { return nil }

        let time = CMTime(seconds: seconds, preferredTimescale: 600)
        let timeValue = Int(seconds)

        if let cached = thumbnailCache[timeValue] {
            return cached
        }

        do {
            let cgImage = try await generator.image(at: time).image
            let image = UIImage(cgImage: cgImage)
            thumbnailCache[timeValue] = image
            return image
        } catch {
            return nil
        }
    }

    func generateThumbnails(interval: Double = 1.0) async -> [Double: UIImage] {
        guard let generator, assetDuration > 0 else { return [:] }

        let steps = Int(assetDuration / interval)
        var results: [Double: UIImage] = [:]

        for step in 0..<min(steps, 600) {
            let seconds = Double(step) * interval
            let time = CMTime(seconds: seconds, preferredTimescale: 600)

            do {
                let cgImage = try await generator.image(at: time).image
                let image = UIImage(cgImage: cgImage)
                results[seconds] = image
                thumbnailCache[Int(seconds)] = image
            } catch {
                continue
            }
        }

        return results
    }

    func invalidate() {
        thumbnailCache.removeAll()
        generator = nil
        assetURL = nil
        assetDuration = 0
    }
}
