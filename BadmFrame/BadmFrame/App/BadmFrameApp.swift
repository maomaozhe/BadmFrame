import SwiftUI
import SwiftData

@main
struct BadmFrameApp: App {
    let container: ModelContainer

    init() {
        do {
            let schema = Schema([Project.self, SourceVideo.self, Marker.self, Clip.self])
            let config = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
            container = try ModelContainer(for: schema, configurations: [config])
        } catch {
            fatalError("无法初始化数据模型容器: \(error.localizedDescription)")
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(container)
    }
}
