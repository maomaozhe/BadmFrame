import { useEffect, useMemo, useState } from "react";
import { useProjectStore } from "@/store/projectSlice";
import { useVideoStore } from "@/store/videoSlice";
import { useUIStore } from "@/store/uiSlice";
import { useMarkerStore } from "@/store/markerSlice";
import { useRallyStore } from "@/store/rallySlice";
import { VideoPlayer } from "./VideoPlayer";
import { TimelineView } from "@/components/Timeline/TimelineView";
import { MarkerPanel } from "@/components/Markers/MarkerPanel";
import { ClipPanel } from "@/components/Clips/ClipPanel";
import { RallyReviewPanel } from "@/components/Rallies/RallyReviewPanel";
import { ExportDialog } from "@/components/Export/ExportDialog";
import { useKeyboard } from "@/hooks/useKeyboard";
import { api } from "@/services/api";
import type { AutoClipDraft, AutoClipMode, AutoClipSegment, EditorTab } from "@/types";

interface Props {
  onBack: () => void;
}

export function EditorView({ onBack }: Props) {
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const projects = useProjectStore((s) => s.projects);
  const loadProjects = useProjectStore((s) => s.loadProjects);
  const { setShowExport } = useUIStore();
  const { selectedTab, setSelectedTab } = useUIStore();
  const currentTime = useVideoStore((s) => s.currentTime);
  const addMarker = useMarkerStore((s) => s.addMarker);
  const rallyStatus = useRallyStore((s) => s.status);
  const rallyCandidates = useRallyStore((s) => s.candidates);
  const selectedRallyId = useRallyStore((s) => s.selectedCandidateId);
  const setRallyStatus = useRallyStore((s) => s.setStatus);
  const setRallyCandidates = useRallyStore((s) => s.setCandidates);
  const selectRally = useRallyStore((s) => s.selectCandidate);

  const project = projects.find((p) => p.id === currentProjectId);
  if (!project) return null;

  const tabs: { key: EditorTab; label: string }[] = [
    { key: "markers", label: "标记" },
    { key: "clips", label: "片段" },
    { key: "rallies", label: "回合检测" },
    { key: "info", label: "信息" },
  ];

  const visibleAutoSegments = useMemo(
    () => autoDraft?.segments ?? [],
    [autoDraft]
  );

  useEffect(() => {
    if (!project?.sourceVideo?.serverVideoId) return;
    let cancelled = false;
    api.getLatestAnalysis(project.id)
      .then((latest) => {
        if (!latest || cancelled || !project.sourceVideo?.serverVideoId) return;
        return api.getAnalysis(project.sourceVideo.serverVideoId, latest.task_id);
      })
      .then((draft) => {
        if (draft && !cancelled) setAutoDraft(draft);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [project?.id, project?.sourceVideo?.serverVideoId]);

  const runAutoClipDraft = async (mode: AutoClipMode) => {
    const duration = project.sourceVideo?.durationSec ?? 0;
    const videoId = project.sourceVideo?.serverVideoId || project.sourceVideo?.id;
    if (!videoId) return;
    setSelectedTab("auto");
    setAutoDraft({
      status: "running",
      mode,
      progress: 0.2,
      segments: [],
      stage: "uploading",
      message: "Uploading video for TrackNetV3 inference",
      createdAt: new Date().toISOString(),
    });

    try {
      const started = await api.startAnalysis(videoId, mode);
      const draft = await api.getAnalysis(videoId, started.task_id);
      setAutoDraft(draft);
    } catch (e: any) {
      setAutoDraft({
        status: "failed",
        mode,
        progress: 0,
        segments: [],
        error: e.message || "分析失败",
        createdAt: new Date().toISOString(),
      });
    }
  };

  const updateAutoSegment = (segmentId: string, updates: Partial<AutoClipSegment>) => {
    setAutoDraft((draft) => {
      if (!draft) return draft;
      return {
        ...draft,
        segments: draft.segments.map((segment) =>
          segment.id === segmentId ? { ...segment, ...updates } : segment
        ),
      };
    });
  };

  const applyAutoClips = async () => {
    if (!autoDraft?.taskId) return;
    await api.applyAutoClips(project.id, autoDraft.taskId);
    await loadProjects();
    useProjectStore.getState().setCurrentProject(project.id);
    setSelectedTab("clips");
  };

  useKeyboard(
    {
      Space: () => {
        const video = document.querySelector("video");
        if (video) video.paused ? video.play() : video.pause();
      },
      KeyM: () => addMarker(currentTime),
    },
    true,
  );

  return (
    <div className="h-full flex flex-col overflow-hidden">
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
            onClick={() => void runRallyDetection()}
            className="px-3 py-1 text-sm rounded-md border hover:bg-accent disabled:opacity-50"
            disabled={!project.sourceVideo || rallyStatus === "running"}
          >
            {rallyStatus === "running" ? "检测中..." : "检测回合"}
          </button>
          <button
            onClick={() => setShowExport(true)}
            className="px-3 py-1 text-sm rounded-md border hover:bg-accent disabled:opacity-50"
            disabled={!hasExportableContent}
          >
            导出
          </button>
        </div>
      </header>

      <VideoPlayer />

      <TimelineView
        duration={project.sourceVideo?.durationSec ?? 0}
        markers={project.markers}
        rallyCandidates={rallyCandidates}
        selectedRallyId={selectedRallyId}
        onSelectRally={selectRally}
        onAddMarker={() => addMarker(currentTime)}
      />

      <div className="flex-1 overflow-y-auto border-t">
        {selectedTab === "markers" && (
          <MarkerPanel markers={project.markers} />
        )}
        {selectedTab === "clips" && (
          <ClipPanel clips={project.clips} duration={project.sourceVideo?.durationSec ?? 0} />
        )}
        {selectedTab === "auto" && (
          <AutoClipPanel
            draft={autoDraft}
            duration={project.sourceVideo?.durationSec ?? 0}
            onRun={runAutoClipDraft}
            onUpdateSegment={updateAutoSegment}
            onApply={applyAutoClips}
          />
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
