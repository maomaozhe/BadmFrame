import Foundation
import AVFoundation
import SwiftUI
import PhotosUI
import UniformTypeIdentifiers

struct VideoMetadata {
    let fileName: String
    let durationSec: Double
    let width: Int
    let height: Int
    let frameRate: Double
    let codec: String
    let isVFR: Bool
    let fileSize: Int64
}

enum ImportError: LocalizedError {
    case loadFailed
    case copyFailed(Error)
    case metadataFailed(Error)

    var errorDescription: String? {
        switch self {
        case .loadFailed: return "无法加载所选视频"
        case .copyFailed(let e): return "拷贝视频失败: \(e.localizedDescription)"
        case .metadataFailed(let e): return "读取视频信息失败: \(e.localizedDescription)"
        }
    }
}

@Observable
final class VideoImportService {
    private let mediaDir: URL

    init() {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        mediaDir = docs.appendingPathComponent("BadmFrame/media", isDirectory: true)
        try? FileManager.default.createDirectory(at: mediaDir, withIntermediateDirectories: true)
    }

    func importVideo(from result: PHPickerResult) async throws -> (VideoMetadata, URL) {
        let data = try await loadItem(from: result)
        guard let originalURL = data.url else {
            throw ImportError.loadFailed
        }

        let fileName = originalURL.lastPathComponent
        let destURL = uniqueURL(for: fileName)
        try FileManager.default.copyItem(at: originalURL, to: destURL)

        let metadata = try await extractMetadata(from: destURL, fileName: fileName)
        return (metadata, destURL)
    }

    func importVideo(from item: PhotosPickerItem) async throws -> (VideoMetadata, URL) {
        guard let data = try await item.loadTransferable(type: Data.self) else {
            throw ImportError.loadFailed
        }

        let ext = item.supportedContentTypes.first?.preferredFilenameExtension ?? "mov"
        let fileName = "imported_video_\(UUID().uuidString).\(ext)"
        let destURL = uniqueURL(for: fileName)
        do {
            try data.write(to: destURL, options: .atomic)
        } catch {
            throw ImportError.copyFailed(error)
        }

        let metadata = try await extractMetadata(from: destURL, fileName: fileName)
        return (metadata, destURL)
    }

    func storageInfo() -> (used: Int64, available: Int64) {
        do {
            let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            let values = try docs.resourceValues(forKeys: [.volumeTotalCapacityKey, .volumeAvailableCapacityKey])
            let total = Int64(values.volumeTotalCapacity ?? 0)
            let avail = Int64(values.volumeAvailableCapacity ?? 0)
            let used = total - avail
            return (used, avail)
        } catch {
            return (0, 0)
        }
    }

    func deleteMedia(at url: URL) {
        try? FileManager.default.removeItem(at: url)
    }

    // MARK: - Private

    private func loadItem(from result: PHPickerResult) async throws -> (url: URL?, data: Data?) {
        typealias ItemResult = (url: URL?, data: Data?)
        return try await withCheckedThrowingContinuation { continuation in
            result.itemProvider.loadFileRepresentation(forTypeIdentifier: UTType.movie.identifier) { url, error in
                if let error {
                    continuation.resume(throwing: error)
                } else {
                    continuation.resume(returning: (url, nil))
                }
            }
        }
    }

    private func uniqueURL(for fileName: String) -> URL {
        let base = mediaDir.appendingPathComponent(fileName)
        let stem = base.deletingPathExtension().lastPathComponent
        let ext = base.pathExtension.isEmpty ? "mp4" : base.pathExtension

        var counter = 0
        var url = base
        while FileManager.default.fileExists(atPath: url.path) {
            counter += 1
            url = mediaDir.appendingPathComponent("\(stem)_\(counter).\(ext)")
        }
        return url
    }

    private func extractMetadata(from url: URL, fileName: String) async throws -> VideoMetadata {
        let asset = AVAsset(url: url)
        do {
            let duration = try await asset.load(.duration)
            let tracks = try await asset.load(.tracks)
            let videoTrack = tracks.first(where: { $0.mediaType == .video })

            let durSec = CMTimeGetSeconds(duration)
            let size = try await videoTrack?.load(.naturalSize) ?? .zero
            let rate = try await videoTrack?.load(.nominalFrameRate) ?? 0
            let codec = videoTrack.flatMap { Self.codecDescription(for: $0) } ?? "未知"

            var isVFR = false
            if let track = videoTrack {
                let formatDescriptions = (try? await track.load(.formatDescriptions)) ?? []
                for fd in formatDescriptions {
                    let fdRef = fd as! CMFormatDescription
                    let mediaSubType = CMFormatDescriptionGetMediaSubType(fdRef)
                    if mediaSubType == kCMVideoCodecType_HEVC || mediaSubType == kCMVideoCodecType_H264 {
                        // phone videos often VFR
                    }
                }
            }

            let attrs = try FileManager.default.attributesOfItem(atPath: url.path)
            let fileSize = attrs[.size] as? Int64 ?? 0

            return VideoMetadata(
                fileName: fileName,
                durationSec: durSec,
                width: Int(size.width),
                height: Int(size.height),
                frameRate: Double(rate),
                codec: codec,
                isVFR: isVFR,
                fileSize: fileSize
            )
        } catch {
            throw ImportError.metadataFailed(error)
        }
    }

    private static func codecDescription(for track: AVAssetTrack) -> String? {
        let descs = track.formatDescriptions as! [CMFormatDescription]
        guard let first = descs.first else { return nil }
        let codec = CMFormatDescriptionGetMediaSubType(first)
        switch codec {
        case kCMVideoCodecType_H264: return "H.264"
        case kCMVideoCodecType_HEVC: return "HEVC"
        case kCMVideoCodecType_AppleProRes422: return "ProRes 422"
        case kCMVideoCodecType_AppleProRes4444: return "ProRes 4444"
        default:
            let chars = [(codec >> 24) & 0xFF, (codec >> 16) & 0xFF, (codec >> 8) & 0xFF, codec & 0xFF]
            return String(bytes: chars.map { UInt8($0) }, encoding: .ascii)
        }
    }
}
