import { useClipStore } from "@/store/clipSlice";
import { formatTimePrecise } from "@/utils";
import type { Clip } from "@/types";

interface Props {
  clips: Clip[];
  duration: number;
}

export function ClipPanel({ clips, duration }: Props) {
  const { deleteClip } = useClipStore();

  const seekTo = (t: number) => {
    const video = document.querySelector("video");
    if (video) video.currentTime = t;
  };

  if (clips.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground gap-2 py-12">
        <span className="text-3xl">✂️</span>
        <p className="text-sm">还没有片段</p>
        <p className="text-xs">从标记点创建片段，或手动设置起止时间</p>
      </div>
    );
  }

  const sorted = [...clips].sort((a, b) => a.startTimeSec - b.startTimeSec);

  return (
    <div className="divide-y">
      {sorted.map((clip) => (
        <div key={clip.id} className="px-3 py-2 hover:bg-accent/50 group">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate flex-1">
              {clip.label || "未命名片段"}
            </span>
            <StatusBadge status={clip.exportStatus} />
          </div>
          <div className="flex items-center gap-2 mt-1">
            <button onClick={() => seekTo(clip.startTimeSec)} className="text-xs text-blue-500 font-mono hover:underline">
              {formatTimePrecise(clip.startTimeSec)}
            </button>
            <span className="text-xs text-muted-foreground">→</span>
            <button onClick={() => seekTo(clip.endTimeSec)} className="text-xs text-blue-500 font-mono hover:underline">
              {formatTimePrecise(clip.endTimeSec)}
            </button>
            <span className="text-xs text-muted-foreground">
              ({formatTimePrecise(clip.endTimeSec - clip.startTimeSec)})
            </span>
            <div className="hidden group-hover:flex items-center gap-1 ml-auto">
              <button onClick={() => deleteClip(clip.id)} className="text-xs px-1.5 py-0.5 text-destructive rounded hover:bg-destructive/10">
                🗑
              </button>
            </div>
          </div>
          {clip.notes && (
            <p className="text-xs text-muted-foreground mt-1 truncate">{clip.notes}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: Clip["exportStatus"] }) {
  if (status === "none") return null;
  if (status === "exporting") return <span className="text-xs text-blue-500">导出中...</span>;
  if (status === "completed") return <span className="text-xs px-1.5 py-0.5 rounded-full bg-green-100 text-green-700">已导出</span>;
  if (status === "failed") return <span className="text-xs px-1.5 py-0.5 rounded-full bg-red-100 text-red-600">失败</span>;
  return null;
}
