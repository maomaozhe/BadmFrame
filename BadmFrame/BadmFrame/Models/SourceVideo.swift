import Foundation
import SwiftData

@Model
final class SourceVideo {
    var fileName: String = ""
    var filePath: String = ""
    var durationSec: Double = 0
    var width: Int = 0
    var height: Int = 0
    var frameRate: Double = 0
    var codec: String = ""
    var isVFR: Bool = false
    var fileSize: Int64 = 0
    var importDate: Date = Date()

    @Relationship(inverse: \Project.sourceVideo) var project: Project?

    init(fileName: String, filePath: String, durationSec: Double, width: Int, height: Int, frameRate: Double, codec: String, isVFR: Bool, fileSize: Int64) {
        self.fileName = fileName
        self.filePath = filePath
        self.durationSec = durationSec
        self.width = width
        self.height = height
        self.frameRate = frameRate
        self.codec = codec
        self.isVFR = isVFR
        self.fileSize = fileSize
        self.importDate = Date()
    }

    var resolutionDisplay: String { "\(width)×\(height)" }

    var frameRateDisplay: String { String(format: "%.1f fps", frameRate) }

    var fileSizeDisplay: String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: fileSize)
    }
}
