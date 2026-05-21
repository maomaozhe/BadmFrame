import Foundation
import AVFoundation

enum ExportError: LocalizedError {
    case invalidTimeRange
    case sessionCreationFailed
    case exportFailed(String)
    case cancelled

    var errorDescription: String? {
        switch self {
        case .invalidTimeRange: return "无效的时间范围"
        case .sessionCreationFailed: return "无法创建导出会话"
        case .exportFailed(let msg): return "导出失败: \(msg)"
        case .cancelled: return "导出已取消"
        }
    }
}

@Observable
final class ExportService {
    var progress: Double = 0
    var isExporting: Bool = false
    private var currentSession: AVAssetExportSession?

    func exportClip(sourcePath: String, startTime: Double, endTime: Double, outputName: String) async throws -> URL {
        let sourceURL = URL(fileURLWithPath: sourcePath)
        let asset = AVAsset(url: sourceURL)

        let outDir = sourceURL.deletingLastPathComponent()
            .appendingPathComponent("exports", isDirectory: true)
        try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
        let outputURL = outDir.appendingPathComponent(outputName)

        if FileManager.default.fileExists(atPath: outputURL.path) {
            try? FileManager.default.removeItem(at: outputURL)
        }

        guard let session = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetPassthrough) else {
            throw ExportError.sessionCreationFailed
        }

        let start = CMTime(seconds: startTime, preferredTimescale: 600)
        let end = CMTime(seconds: endTime, preferredTimescale: 600)
        let range = CMTimeRange(start: start, end: end)

        guard CMTIMERANGE_IS_VALID(range) && CMTimeCompare(range.duration, .zero) > 0 else {
            throw ExportError.invalidTimeRange
        }

        session.timeRange = range
        session.outputURL = outputURL
        session.outputFileType = .mp4

        currentSession = session
        isExporting = true
        progress = 0

        await withCheckedContinuation { continuation in
            let timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] t in
                self?.progress = Double(session.progress)
                if session.status != .exporting && session.status != .waiting {
                    t.invalidate()
                }
            }

            session.exportAsynchronously {
                timer.invalidate()
                continuation.resume()
            }
        }

        isExporting = false

        switch session.status {
        case .completed:
            progress = 1.0
            return outputURL
        case .cancelled:
            throw ExportError.cancelled
        case .failed:
            throw ExportError.exportFailed(session.error?.localizedDescription ?? "未知错误")
        default:
            throw ExportError.exportFailed("意外状态: \(session.status.rawValue)")
        }
    }

    func cancelExport() {
        currentSession?.cancelExport()
    }
}
