import { useState } from "react";
import { useProjectStore } from "@/store/projectSlice";
import { useUIStore } from "@/store/uiSlice";
import { useClipStore } from "@/store/clipSlice";
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { formatTimePrecise } from "@/utils";

export function ExportDialog() {
  const { showExport, setShowExport } = useUIStore();
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const projects = useProjectStore((s) => s.projects);
  const { updateExportStatus } = useClipStore();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [results, setResults] = useState<{ clipId: string; label: string; success: boolean }[]>([]);

  const project = projects.find((p) => p.id === currentProjectId);
  if (!project) return null;

  const clips = project.clips;

  const toggle = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const handleExport = async () => {
    if (!project.sourceVideo?.objectURL) return;
    setExporting(true);
    const toExport = clips.filter((c) => selected.has(c.id));
    const res: typeof results = [];

    for (const clip of toExport) {
      try {
        updateExportStatus(clip.id, "exporting");
        await exportClip(project.sourceVideo.objectURL, clip.startTimeSec, clip.endTimeSec, clip.label);
        updateExportStatus(clip.id, "completed");
        res.push({ clipId: clip.id, label: clip.label, success: true });
      } catch {
        updateExportStatus(clip.id, "failed");
        res.push({ clipId: clip.id, label: clip.label, success: false });
      }
    }
    setResults(res);
    setExporting(false);
  };

  const handleClose = () => {
    setShowExport(false);
    setSelected(new Set());
    setResults([]);
  };

  return (
    <Dialog open={showExport} onClose={handleClose}>
      <DialogHeader>
        <DialogTitle>{results.length > 0 ? "导出完成" : "导出片段"}</DialogTitle>
      </DialogHeader>

      {results.length > 0 ? (
        <>
          <div className="px-6 py-4 space-y-2">
            <p className="text-sm text-center">
              成功 {results.filter((r) => r.success).length} / {results.length} 个片段
            </p>
            {results.map((r) => (
              <div key={r.clipId} className="flex items-center gap-2 text-sm">
                <span>{r.success ? "✅" : "❌"}</span>
                <span className="truncate">{r.label || "片段"}</span>
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button onClick={handleClose}>完成</Button>
          </DialogFooter>
        </>
      ) : (
        <>
          <div className="px-6 py-4 max-h-64 overflow-y-auto space-y-1">
            {clips.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">暂无片段可供导出</p>
            ) : (
              clips.map((clip) => (
                <div
                  key={clip.id}
                  className={`flex items-center gap-2 p-2 rounded cursor-pointer text-sm ${
                    selected.has(clip.id) ? "bg-primary/10" : "hover:bg-accent"
                  }`}
                  onClick={() => toggle(clip.id)}
                >
                  <input type="checkbox" checked={selected.has(clip.id)} readOnly className="w-4 h-4" />
                  <span className="flex-1 truncate">{clip.label || "未命名"}</span>
                  <span className="text-xs text-muted-foreground font-mono">
                    {formatTimePrecise(clip.startTimeSec)} → {formatTimePrecise(clip.endTimeSec)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    ({formatTimePrecise(clip.endTimeSec - clip.startTimeSec)})
                  </span>
                </div>
              ))
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>取消</Button>
            <Button onClick={handleExport} disabled={exporting || selected.size === 0}>
              {exporting ? "导出中..." : `导出 (${selected.size})`}
            </Button>
          </DialogFooter>
        </>
      )}
    </Dialog>
  );
}

function exportClip(videoURL: string, start: number, end: number, label: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    video.src = videoURL;
    video.preload = "auto";
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d")!;

    const recorder = new MediaRecorder(
      (canvas as any).captureStream(30),
      { mimeType: "video/webm;codecs=vp9" }
    );
    const chunks: BlobPart[] = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: "video/webm" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${label || "clip"}_${Math.floor(start)}s-${Math.floor(end)}s.webm`;
      a.click();
      URL.revokeObjectURL(url);
      resolve();
    };
    recorder.onerror = () => reject(new Error("录制失败"));

    video.onloadedmetadata = () => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      video.currentTime = start;
      video.onseeked = () => {
        const drawFrame = () => {
          if (video.currentTime >= end || video.ended) {
            recorder.stop();
            video.pause();
            return;
          }
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          requestAnimationFrame(drawFrame);
        };
        video.play();
        recorder.start();
        drawFrame();
      };
    };
    video.onerror = () => reject(new Error("视频加载失败"));
  });
}
