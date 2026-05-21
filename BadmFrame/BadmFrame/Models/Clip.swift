import Foundation
import SwiftData

@Model
final class Clip {
    var startTimeSec: Double = 0
    var endTimeSec: Double = 0
    var label: String = ""
    var notes: String = ""
    var anchorMarkerId: String?
    var exportStatusRaw: String = ClipExportStatus.none.rawValue
    var exportedFilePath: String?
    var createdAt: Date = Date()

    var project: Project?

    enum ClipExportStatus: String {
        case none = "none"
        case exporting = "exporting"
        case completed = "completed"
        case failed = "failed"
    }

    init(startTimeSec: Double, endTimeSec: Double, label: String = "", notes: String = "", anchorMarkerId: String? = nil) {
        self.startTimeSec = startTimeSec
        self.endTimeSec = endTimeSec
        self.label = label
        self.notes = notes
        self.anchorMarkerId = anchorMarkerId
        self.createdAt = Date()
    }

    var durationSec: Double { endTimeSec - startTimeSec }

    var startTimeDisplay: String { startTimeSec.preciseDisplayString }
    var endTimeDisplay: String { endTimeSec.preciseDisplayString }
    var durationDisplay: String { durationSec.preciseDisplayString }

    var exportStatus: ClipExportStatus {
        get { ClipExportStatus(rawValue: exportStatusRaw) ?? .none }
        set { exportStatusRaw = newValue.rawValue }
    }
}
