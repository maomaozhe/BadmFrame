import SwiftUI
import SwiftData
import PhotosUI

struct ProjectListView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \Project.updatedAt, order: .reverse) private var projects: [Project]
    @State private var showingImport = false
    @State private var projectListVM = ProjectListViewModel()

    var body: some View {
        Group {
            if projects.isEmpty {
                EmptyStateView(
                    icon: "figure.badminton",
                    title: "还没有打球记录",
                    subtitle: "导入一段羽毛球视频开始吧",
                    action: { showingImport = true },
                    actionLabel: "导入视频"
                )
            } else {
                List {
                    ForEach(projects) { project in
                        NavigationLink(value: project) {
                            ProjectRowView(project: project)
                        }
                    }
                    .onDelete { indexSet in
                        for i in indexSet {
                            projectListVM.deleteProject(projects[i], context: modelContext)
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("BadmFrame")
        .navigationDestination(for: Project.self) { project in
            EditorView(project: project)
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showingImport = true
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .sheet(isPresented: $showingImport) {
            ImportVideoView { newProject in
                showingImport = false
            }
        }
    }
}

struct ProjectRowView: View {
    let project: Project

    var body: some View {
        HStack(spacing: 12) {
            RoundedRectangle(cornerRadius: 6)
                .fill(Color.secondary.opacity(0.15))
                .frame(width: 60, height: 40)
                .overlay {
                    Image(systemName: "play.rectangle")
                        .foregroundStyle(.secondary)
                }

            VStack(alignment: .leading, spacing: 2) {
                Text(project.name)
                    .font(.headline)

                if let video = project.sourceVideo {
                    Text("\(video.durationSec.preciseDisplayString) · \(video.resolutionDisplay)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                HStack(spacing: 8) {
                    Label("\(project.markerCount)", systemImage: "pin.fill")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Label("\(project.clipCount)", systemImage: "scissors")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text(project.createdAtDisplay)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
    }
}
