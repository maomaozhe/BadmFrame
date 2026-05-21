import Foundation
import SwiftData

@Observable
final class ProjectListViewModel {
    var errorMessage: String?

    func createProject(name: String, context: ModelContext) -> Project {
        let project = Project(name: name)
        context.insert(project)
        try? context.save()
        return project
    }

    func deleteProject(_ project: Project, context: ModelContext) {
        if let path = project.sourceVideo?.filePath {
            try? FileManager.default.removeItem(atPath: path)
        }
        context.delete(project)
        try? context.save()
    }

    func updateProjectName(_ project: Project, name: String, context: ModelContext) {
        project.name = name
        project.updatedAt = Date()
        try? context.save()
    }
}
