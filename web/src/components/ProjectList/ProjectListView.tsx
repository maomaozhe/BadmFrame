import { useProjectStore } from "@/store/projectSlice";
import { formatTime, formatTimePrecise } from "@/utils";

interface Props {
  onProjectCreated: (id: string) => void;
}

export function ProjectListView({}: Props) {
  const { projects, setCurrentProject, deleteProject } = useProjectStore();

  if (projects.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center gap-4 px-4">
        <span className="text-5xl">🏸</span>
        <div>
          <p className="text-lg font-medium">还没有打球记录</p>
          <p className="text-sm text-muted-foreground mt-1">
            导入一段羽毛球视频，开始标记精彩瞬间
          </p>
        </div>
      </div>
    );
  }

  return (
    <main className="flex-1 overflow-y-auto">
      {projects.map((project) => (
        <div
          key={project.id}
          className="border-b px-4 py-3 flex items-center gap-3 hover:bg-accent/50 cursor-pointer group"
          onClick={() => setCurrentProject(project.id)}
        >
          <div className="w-16 h-10 rounded bg-primary/10 flex items-center justify-center shrink-0">
            <span className="text-muted-foreground text-lg">▶</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">{project.name}</p>
            <p className="text-xs text-muted-foreground">
              {project.sourceVideo ? (
                <>
                  {formatTimePrecise(project.sourceVideo.durationSec)} · {project.sourceVideo.width}×{project.sourceVideo.height}
                </>
              ) : (
                "未导入视频"
              )}
              {" · "}
              {project.markers.length} 个标记 · {project.clips.length} 个片段
            </p>
            <p className="text-xs text-muted-foreground">
              {new Date(project.createdAt).toLocaleDateString("zh-CN", {
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (confirm("确定删除这个项目吗？")) deleteProject(project.id);
            }}
            className="text-sm text-destructive opacity-0 group-hover:opacity-100 transition-opacity px-2"
          >
            删除
          </button>
        </div>
      ))}
    </main>
  );
}
