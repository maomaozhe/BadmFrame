import Foundation
import SwiftData
import SwiftUI

@Observable
final class MarkerViewModel {
    var errorMessage: String?

    func addMarker(at seconds: Double, label: String = "", colorName: String = "yellow", project: Project, context: ModelContext) -> Marker {
        let marker = Marker(timestampSec: seconds, label: label, colorName: colorName)
        context.insert(marker)
        marker.project = project
        project.markers.append(marker)
        try? context.save()
        return marker
    }

    func deleteMarker(_ marker: Marker, from project: Project, context: ModelContext) {
        if let index = project.markers.firstIndex(where: { $0.id == marker.id }) {
            project.markers.remove(at: index)
        }
        context.delete(marker)
        try? context.save()
    }

    func updateMarkerLabel(_ marker: Marker, label: String, context: ModelContext) {
        marker.label = label
        try? context.save()
    }

    func updateMarkerColor(_ marker: Marker, colorName: String, context: ModelContext) {
        marker.colorName = colorName
        try? context.save()
    }
}
