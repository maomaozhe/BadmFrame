import Foundation
import SwiftData

@Observable
final class ClipViewModel {
    var errorMessage: String?

    func createClip(
        startTime: Double,
        endTime: Double,
        label: String = "",
        notes: String = "",
        anchorMarkerId: String? = nil,
        project: Project,
        context: ModelContext
    ) -> Clip {
        let clip = Clip(
            startTimeSec: startTime,
            endTimeSec: endTime,
            label: label,
            notes: notes,
            anchorMarkerId: anchorMarkerId
        )
        context.insert(clip)
        clip.project = project
        project.clips.append(clip)
        try? context.save()
        return clip
    }

    func deleteClip(_ clip: Clip, from project: Project, context: ModelContext) {
        if let exportedPath = clip.exportedFilePath {
            try? FileManager.default.removeItem(atPath: exportedPath)
        }
        if let index = project.clips.firstIndex(where: { $0.id == clip.id }) {
            project.clips.remove(at: index)
        }
        context.delete(clip)
        try? context.save()
    }

    func updateClipTimeRange(_ clip: Clip, start: Double, end: Double, context: ModelContext) {
        clip.startTimeSec = start
        clip.endTimeSec = end
        try? context.save()
    }

    func updateClipNotes(_ clip: Clip, label: String, notes: String, context: ModelContext) {
        clip.label = label
        clip.notes = notes
        try? context.save()
    }

    func updateExportStatus(_ clip: Clip, status: Clip.ClipExportStatus, filePath: String? = nil, context: ModelContext) {
        clip.exportStatus = status
        if let path = filePath {
            clip.exportedFilePath = path
        }
        try? context.save()
    }
}
