import { useProjectStore } from "@/store/projectSlice";
import { useVideoStore } from "@/store/videoSlice";
import { useUIStore } from "@/store/uiSlice";
import { useMarkerStore } from "@/store/markerSlice";
import { useClipStore } from "@/store/clipSlice";
import { VideoPlayer } from "./VideoPlayer";
import { TimelineView } from "@/components/Timeline/TimelineView";
import { MarkerPanel } from "@/components/Markers/MarkerPanel";
import { ClipPanel } from "@/components/Clips/ClipPanel";
import { ExportDialog } from "@/components/Export/ExportDialog";
import { useKeyboard } from "@/hooks/useKeyboard";
import type { EditorTab } from "@/types";

interface Props {
  onBack: () => void;
}

export function EditorView({ onBack }: Props) {
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const projects = useProjectStore((s) => s.projects);
  const { setShowExport } = useUIStore();
  const { selectedTab, setSelectedTab } = useUIStore();
  const currentTime = useVideoStore((s) => s.currentTime);
  const addMarker = useMarkerStore((s) => s.addMarker);

  const project = projects.find((p) => p.id === currentProjectId);
  if (!project) return null;

  const tabs: { key: EditorTab; label: string }[] = [
    { key: "markers", label: "标记" },
    { key: "clips", label: "片段" },
    { key: "info", label: "信息" },
  ];

  useKeyboard(
    {
      Space: () => {
        const video = document.querySelector("video");
        if (video) video.paused ? video.play() : video.pause();
      },
      KeyM: () => addMarker(currentTime),
    },
    true
  );

  return (
    <div className="h-full flex flex-col">
      <header className="border-b px-3 py-2 flex items-center gap-3 shrink-0">
        <button onClick={onBack} className="text-sm text-muted-foreground hover:text-foreground">
          ← 返回
        </button>
        <h2 className="font-semibold truncate flex-1">{project.name}</h2>
        <div className="flex gap-1">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setSelectedTab(t.key)}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                selectedTab === t.key
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
          <button
            onClick={() => setShowExport(true)}
            className="px-3 py-1 text-sm rounded-md border hover:bg-accent"
            disabled={project.clips.length === 0}
          >
            导出
          </button>
        </div>
      </header>

      <VideoPlayer />

      <TimelineView
        duration={project.sourceVideo?.durationSec ?? 0}
        markers={project.markers}
        onAddMarker={() => addMarker(currentTime)}
      />

      <div className="flex-1 overflow-y-auto border-t">
        {selectedTab === "markers" && (
          <MarkerPanel markers={project.markers} />
        )}
        {selectedTab === "clips" && (
          <ClipPanel clips={project.clips} duration={project.sourceVideo?.durationSec ?? 0} />
        )}
        {selectedTab === "info" && (
          <div className="p-4 space-y-4 text-sm">
            {project.sourceVideo && (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <span className="text-muted-foreground">文件名</span>
                  <span className="truncate">{project.sourceVideo.fileName}</span>
                  <span className="text-muted-foreground">时长</span>
                  <span>{formatTimePrecise(project.sourceVideo.durationSec)}</span>
                  <span className="text-muted-foreground">分辨率</span>
                  <span>{project.sourceVideo.width}×{project.sourceVideo.height}</span>
                  <span className="text-muted-foreground">编码</span>
                  <span>{project.sourceVideo.codec}</span>
                  {project.sourceVideo.isVFR && (
                    <>
                      <span className="text-muted-foreground">可变帧率</span>
                      <span className="text-yellow-500">⚠ 是</span>
                    </>
                  )}
                </div>
              </>
            )}
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">标记数量</span>
              <span>{project.markers.length}</span>
              <span className="text-muted-foreground">片段数量</span>
              <span>{project.clips.length}</span>
              <span className="text-muted-foreground">创建时间</span>
              <span>{new Date(project.createdAt).toLocaleString("zh-CN")}</span>
            </div>
          </div>
        )}
      </div>

      <ExportDialog />
    </div>
  );
}

function formatTimePrecise(seconds: number): string {
  const ts = Math.floor(seconds);
  const m = Math.floor(ts / 60);
  const s = ts % 60;
  const cs = Math.floor((seconds - ts) * 100);
  return `${m}:${String(s).padStart(2, "0")}.${String(cs).padStart(2, "0")}`;
}
