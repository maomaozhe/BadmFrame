import Foundation
import SwiftData
import SwiftUI

@Model
final class Marker {
    var timestampSec: Double = 0
    var label: String = ""
    var colorName: String = "yellow"
    var createdAt: Date = Date()

    var project: Project?

    init(timestampSec: Double, label: String = "", colorName: String = "yellow") {
        self.timestampSec = timestampSec
        self.label = label
        self.colorName = colorName
        self.createdAt = Date()
    }

    var timestampDisplay: String {
        let totalSeconds = Int(timestampSec)
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        let centiseconds = Int((timestampSec - Double(totalSeconds)) * 100)
        return String(format: "%d:%02d.%02d", minutes, seconds, centiseconds)
    }

    var color: Color {
        switch colorName {
        case "red": return .red
        case "blue": return .blue
        case "green": return .green
        case "orange": return .orange
        case "purple": return .purple
        default: return .yellow
        }
    }

    static let availableColors: [(name: String, displayName: String)] = [
        ("yellow", "黄色"),
        ("red", "红色"),
        ("blue", "蓝色"),
        ("green", "绿色"),
        ("orange", "橙色"),
        ("purple", "紫色"),
    ]
}
