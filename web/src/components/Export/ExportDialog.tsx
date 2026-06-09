import { useMemo, useState } from "react";
import { api } from "@/services/api";
import { useProjectStore } from "@/store/projectSlice";
import { useUIStore } from "@/store/uiSlice";
import { useClipStore } from "@/store/clipSlice";
import { useRallyStore } from "@/store/rallySlice";
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { formatTimePrecise } from "@/utils";
import type { Clip, ExportSortMode } from "@/types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");

type ExportResult = { clipId: string; label: string; success: boolean; path?: string };

interface ExportableItem {
  id: string;
  startSec: number;
  endSec: number;
  label: string;
  duration: number;
  source: "clip" | "rally";
  candidateId?: string;
}

type ExportPhase = "idle" | "exporting" | "done";

export function ExportDialog() {
  const { showExport, setShowExport, exportSortMode, setExportSortMode } = useUIStore();
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const projects = useProjectStore((s) => s.projects);
  const updateProject = useProjectStore((s) => s.updateProject);
  const { updateExportStatus } = useClipStore();
  const rallyCandidates = useRallyStore((s) => s.candidates);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [phase, setPhase] = useState<ExportPhase>("idle");
  const [results, setResults] = useState<ExportResult[]>([]);
  const [error, setError] = useState("");
  const [exportProgress, setExportProgress] = useState({ current: 0, total: 0 });

  const project = projects.find((p) => p.id === currentProjectId);
  if (!project) return null;

  // Build unified exportable items from clips + accepted/adjusted rally candidates
  const exportableItems: ExportableItem[] = useMemo(() => {
    const items: ExportableItem[] = [];
    const clipStartSecs = new Set(project.clips.map((c) => Math.round(c.startTimeSec * 10)));

    for (const clip of project.clips) {
      items.push({
        id: `clip:${clip.id}`,
        startSec: clip.startTimeSec,
        endSec: clip.endTimeSec,
        label: clip.label || "未命名",
        duration: clip.endTimeSec - clip.startTimeSec,
        source: "clip",
      });
    }

    for (const candidate of rallyCandidates) {
      if (candidate.reviewState === "rejected") continue;
      if (candidate.endSec <= candidate.startSec) continue;
      if (clipStartSecs.has(Math.round(candidate.startSec * 10))) continue;
      items.push({
        id: `rally:${candidate.id}`,
        startSec: candidate.startSec,
        endSec: candidate.endSec,
        label: `回合 ${candidate.id}`,
        duration: candidate.endSec - candidate.startSec,
        source: "rally",
        candidateId: candidate.id,
      });
    }

    return items;
  }, [project.clips, rallyCandidates]);

  // Sort items based on current sort mode
  const sortedItems = useMemo(() => {
    const sorted = [...exportableItems];
    if (exportSortMode === "duration") {
      sorted.sort((a, b) => b.duration - a.duration);
    } else {
      sorted.sort((a, b) => a.startSec - b.startSec);
    }
    return sorted;
  }, [exportableItems, exportSortMode]);

  const toggleSort = () => {
    const next: ExportSortMode = exportSortMode === "position" ? "duration" : "position";
    setExportSortMode(next);
  };

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelected(next);
  };

  const toggleAll = () => {
    if (selected.size === sortedItems.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(sortedItems.map((item) => item.id)));
    }
  };

  // Items to export: selected items, or all if nothing selected
  const itemsToExport = selected.size > 0
    ? sortedItems.filter((item) => selected.has(item.id))
    : sortedItems;

  // Auto-create clips from rally candidates, return clip IDs
  const ensureClips = async (items: ExportableItem[]): Promise<string[]> => {
    const clipIds: string[] = [];
    const newClips: Clip[] = [];
    const now = new Date().toISOString();

    for (const item of items) {
      if (item.source === "clip") {
        clipIds.push(item.id.replace("clip:", ""));
      } else {
        const tempId = `rally-clip-${item.candidateId}`;
        const clip: Clip = {
          id: tempId,
          startTimeSec: item.startSec,
          endTimeSec: item.endSec,
          label: item.label,
          notes: `source:rally-export candidate:${item.candidateId}`,
          exportStatus: "none",
          createdAt: now,
        };
        try {
          const saved = await api.createClip(currentProjectId!, clip);
          newClips.push(saved);
          clipIds.push(saved.id);
        } catch {
          clipIds.push(tempId);
          newClips.push(clip);
        }
      }
    }

    if (newClips.length > 0) {
      const latest = useProjectStore.getState().projects.find((p) => p.id === currentProjectId);
      if (latest) {
        updateProject(currentProjectId!, { clips: [...latest.clips, ...newClips] });
      }
    }

    return clipIds;
  };

  const triggerDownload = (url: string) => {
    // Open download URL in new tab. Server's Content-Disposition: attachment
    // triggers browser Save As dialog and auto-closes the tab.
    // If server returns an error, user sees it in the new tab.
    window.open(url, "_blank");
  };

  const runExport = async (mode: "merged" | "separate") => {
    if (itemsToExport.length === 0) return;
    setPhase("exporting");
    setError("");
    setExportProgress({ current: 0, total: itemsToExport.length });

    try {
      const clipIds = await ensureClips(itemsToExport);

      let taskId: string;

      if (mode === "merged") {
        setExportProgress({ current: 0, total: 1 });
        const progressTimer = setInterval(() => {
          setExportProgress((p) => ({ ...p, current: Math.min(p.current + 0.1, 0.9) }));
        }, 500);
        try {
          const submitted = await api.submitExport(project.id, clipIds, "merged");
          taskId = submitted.taskId;
          const done = await pollExport(taskId);
          clearInterval(progressTimer);
          const merged = done.results.find((r) => r.id === "merged");
          const success = merged?.status === "completed";
          clipIds.forEach((id) => updateExportStatus(id, success ? "completed" : "failed", merged?.path));
          setExportProgress({ current: 1, total: 1 });
          setResults([{ clipId: "merged", label: "合辑", success, path: merged?.path }]);

          if (success && merged?.path) {
            triggerDownload(`${API_BASE}/exports/${taskId}/download?clip_id=${encodeURIComponent("merged")}`);
          }
        } catch {
          clearInterval(progressTimer);
          throw new Error("导出失败");
        }
      } else {
        itemsToExport.forEach((item) => {
          const clipId = item.source === "clip" ? item.id.replace("clip:", "") : `rally-clip-${item.candidateId}`;
          updateExportStatus(clipId, "exporting");
        });

        const submitted = await api.submitExport(project.id, clipIds, "separate");
        taskId = submitted.taskId;

        const done = await pollExportWithProgress(submitted.taskId, (current, total) => {
          setExportProgress({ current, total });
        });

        const nextResults = itemsToExport.map((item) => {
          const clipId = item.source === "clip" ? item.id.replace("clip:", "") : `rally-clip-${item.candidateId}`;
          const result = done.results.find((r) => r.id === clipId);
          const success = result?.status === "completed";
          updateExportStatus(clipId, success ? "completed" : "failed", result?.path);
          return { clipId, label: item.label, success, path: result?.path };
        });
        setResults(nextResults);

        const firstSuccess = nextResults.find((r) => r.success);
        if (firstSuccess) {
          triggerDownload(`${API_BASE}/exports/${taskId}/download?clip_id=${encodeURIComponent(firstSuccess.clipId)}`);
        }
      }
    } catch (e: any) {
      itemsToExport.forEach((item) => {
        const clipId = item.source === "clip" ? item.id.replace("clip:", "") : `rally-clip-${item.candidateId}`;
        updateExportStatus(clipId, "failed");
      });
      setError(e.message || "导出失败");
    } finally {
      setPhase("done");
    }
  };

  const handleClose = () => {
    setShowExport(false);
    setSelected(new Set());
    setResults([]);
    setError("");
    setPhase("idle");
    setExportProgress({ current: 0, total: 0 });
  };

  return (
    <Dialog open={showExport} onClose={handleClose}>
      <DialogHeader>
        <DialogTitle>
          {phase === "exporting" ? "正在导出..." : phase === "done" ? "导出完成" : "导出片段"}
        </DialogTitle>
      </DialogHeader>

      {phase === "exporting" ? (
        <div className="px-6 py-6 space-y-3 text-center">
          <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{
                width: `${exportProgress.total > 0 ? Math.round((exportProgress.current / exportProgress.total) * 100) : 0}%`,
              }}
            />
          </div>
          <p className="text-sm text-muted-foreground">
            正在处理 {exportProgress.current}/{exportProgress.total}
          </p>
        </div>
      ) : phase === "done" ? (
        <>
          <div className="px-6 py-4 space-y-2">
            <p className="text-sm text-center">
              成功 {results.filter((r) => r.success).length} / {results.length} 项
            </p>
            {results.map((r) => (
              <div key={r.clipId} className="flex items-center gap-2 text-sm">
                <span>{r.success ? "\u2713" : "\u00d7"}</span>
                <span className="truncate">{r.label || "片段"}</span>
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
          <div className="px-6 py-4 space-y-2">
            {error && <p className="mb-2 text-sm text-destructive">{error}</p>}

            {sortedItems.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-sm text-muted-foreground">
                  暂无片段可供导出。请先在回合检测中确认候选回合。
                </p>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 mb-2">
                  <button
                    onClick={toggleSort}
                    className="text-xs border px-2 py-0.5 rounded hover:bg-accent"
                  >
                    排序: {exportSortMode === "position" ? "按时间" : "按时长\u2193"}
                  </button>
                  <button
                    onClick={toggleAll}
                    className="text-xs text-muted-foreground hover:text-foreground ml-auto"
                  >
                    {selected.size === sortedItems.length ? "取消全选" : "全选"}
                  </button>
                </div>

                <div className="max-h-64 overflow-y-auto space-y-1">
                  {sortedItems.map((item, i) => (
                    <div
                      key={item.id}
                      className={`flex items-center gap-2 p-2 rounded cursor-pointer text-sm ${
                        selected.has(item.id) ? "bg-primary/10" : "hover:bg-accent"
                      }`}
                      onClick={() => toggle(item.id)}
                    >
                      <input
                        type="checkbox"
                        checked={selected.has(item.id)}
                        readOnly
                        className="w-4 h-4 shrink-0"
                      />
                      {exportSortMode === "duration" && (
                        <span className="text-xs text-muted-foreground w-5 shrink-0">#{i + 1}</span>
                      )}
                      <span className="flex-1 truncate">{item.label}</span>
                      {item.source === "rally" && (
                        <span className="text-xs rounded bg-amber-500/15 text-amber-700 px-1 shrink-0">回合</span>
                      )}
                      <span className="text-xs text-muted-foreground font-mono shrink-0">
                        {formatTimePrecise(item.startSec)} - {formatTimePrecise(item.endSec)}
                      </span>
                      <span className="text-xs text-muted-foreground shrink-0">
                        ({formatTimePrecise(item.duration)})
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              取消
            </Button>
            <Button
              variant="outline"
              onClick={() => runExport("merged")}
              disabled={phase !== "idle" || itemsToExport.length === 0}
            >
              导出合辑 ({itemsToExport.length})
            </Button>
            <Button
              onClick={() => runExport("separate")}
              disabled={phase !== "idle" || itemsToExport.length === 0}
            >
              分段导出 ({itemsToExport.length})
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

async function pollExportWithProgress(
  taskId: string,
  onProgress: (current: number, total: number) => void,
) {
  for (let i = 0; i < 60; i++) {
    const job = await api.getExport(taskId);
    if (job.status === "completed") {
      onProgress(job.results.length, job.results.length);
      return job;
    }
    if (job.status === "failed") throw new Error(job.error || "导出失败");
    // Estimate progress from completed results
    const done = job.results.filter((r: any) => r.status === "completed").length;
    const total = job.results.length || 1;
    onProgress(done, total);
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  throw new Error("导出仍在处理中，请稍后查看历史");
}
