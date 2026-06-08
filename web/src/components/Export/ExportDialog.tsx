import { useState } from "react";
import { api } from "@/services/api";
import { useProjectStore } from "@/store/projectSlice";
import { useUIStore } from "@/store/uiSlice";
import { useClipStore } from "@/store/clipSlice";
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { formatTimePrecise } from "@/utils";
import type { Clip } from "@/types";

type ExportResult = { clipId: string; label: string; success: boolean; path?: string };

export function ExportDialog() {
  const { showExport, setShowExport } = useUIStore();
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const projects = useProjectStore((s) => s.projects);
  const { updateExportStatus } = useClipStore();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [results, setResults] = useState<ExportResult[]>([]);
  const [error, setError] = useState("");

  const project = projects.find((p) => p.id === currentProjectId);
  if (!project) return null;

  const clips = project.clips;

  const toggle = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const handleExportSeparate = async () => {
    const toExport = clips.filter((clip) => selected.has(clip.id));
    if (toExport.length === 0) return;
    setExporting(true);
    setError("");
    try {
      toExport.forEach((clip) => updateExportStatus(clip.id, "exporting"));
      const submitted = await api.submitExport(project.id, toExport.map((clip) => clip.id), "separate");
      const done = await pollExport(submitted.taskId);
      const nextResults = toExport.map((clip) => {
        const item = done.results.find((result) => result.id === clip.id);
        const success = item?.status === "completed";
        updateExportStatus(clip.id, success ? "completed" : "failed", item?.path);
        return { clipId: clip.id, label: clip.label, success, path: item?.path };
      });
      setResults(nextResults);
    } catch (e: any) {
      toExport.forEach((clip) => updateExportStatus(clip.id, "failed"));
      setError(e.message || "导出失败");
    } finally {
      setExporting(false);
    }
  };

  const handleExportSelectedMerged = async () => {
    await runMergedExport(clips.filter((clip) => selected.has(clip.id)));
  };

  const handleExportAllMerged = async () => {
    await runMergedExport(clips);
  };

  const runMergedExport = async (sourceClips: Clip[]) => {
    const toExport = [...sourceClips].sort((a, b) => a.startTimeSec - b.startTimeSec);
    if (toExport.length === 0) return;
    setExporting(true);
    setError("");
    try {
      toExport.forEach((clip) => updateExportStatus(clip.id, "exporting"));
      const submitted = await api.submitExport(project.id, toExport.map((clip) => clip.id), "merged");
      const done = await pollExport(submitted.taskId);
      const merged = done.results.find((result) => result.id === "merged");
      const success = merged?.status === "completed";
      toExport.forEach((clip) => updateExportStatus(clip.id, success ? "completed" : "failed", merged?.path));
      setResults([{ clipId: "merged", label: "合辑", success, path: merged?.path }]);
    } catch (e: any) {
      toExport.forEach((clip) => updateExportStatus(clip.id, "failed"));
      setResults([{ clipId: "merged", label: "合辑", success: false }]);
      setError(e.message || "导出失败");
    } finally {
      setExporting(false);
    }
  };

  const handleClose = () => {
    setShowExport(false);
    setSelected(new Set());
    setResults([]);
    setError("");
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
              成功 {results.filter((r) => r.success).length} / {results.length} 项
            </p>
            {results.map((r) => (
              <div key={r.clipId} className="flex items-center gap-2 text-sm">
                <span>{r.success ? "✓" : "×"}</span>
                <span className="min-w-16 truncate">{r.label || "片段"}</span>
                {r.path && <span className="truncate text-xs text-muted-foreground">{r.path}</span>}
              </div>
            ))}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button onClick={handleClose}>完成</Button>
          </DialogFooter>
        </>
      ) : (
        <>
          <div className="px-6 py-4 max-h-64 overflow-y-auto space-y-1">
            {error && <p className="mb-2 text-sm text-destructive">{error}</p>}
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
            <Button variant="outline" onClick={handleExportSelectedMerged} disabled={exporting || selected.size === 0}>
              {exporting ? "导出中..." : "导出所选合辑"}
            </Button>
            <Button variant="outline" onClick={handleExportSeparate} disabled={exporting || selected.size === 0}>
              {exporting ? "导出中..." : `分段导出 (${selected.size})`}
            </Button>
            <Button onClick={handleExportAllMerged} disabled={exporting || clips.length === 0}>
              {exporting ? "导出中..." : "一键导出合辑"}
            </Button>
          </DialogFooter>
        </>
      )}
    </Dialog>
  );
}

async function pollExport(taskId: string) {
  for (let i = 0; i < 60; i++) {
    const job = await api.getExport(taskId);
    if (job.status === "completed") return job;
    if (job.status === "failed") throw new Error(job.error || "导出失败");
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  throw new Error("导出仍在处理中，请稍后查看历史");
}
