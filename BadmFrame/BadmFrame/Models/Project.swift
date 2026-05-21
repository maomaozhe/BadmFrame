import Foundation
import SwiftData

@Model
final class Project {
    var name: String = ""
    var createdAt: Date = Date()
    var updatedAt: Date = Date()

    @Relationship(deleteRule: .cascade) var sourceVideo: SourceVideo?
    @Relationship(deleteRule: .cascade, inverse: \Marker.project) var markers: [Marker] = []
    @Relationship(deleteRule: .cascade, inverse: \Clip.project) var clips: [Clip] = []

    init(name: String) {
        self.name = name
        self.createdAt = Date()
        self.updatedAt = Date()
    }

    var totalDurationSec: Double {
        sourceVideo?.durationSec ?? 0
    }

    var markerCount: Int { markers.count }
    var clipCount: Int { clips.count }

    var createdAtDisplay: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: createdAt)
    }
}
