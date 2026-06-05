import { useMemo, useState } from "react";
import { useProjectStore } from "@/store/projectSlice";
import { useVideoStore } from "@/store/videoSlice";
import { useUIStore } from "@/store/uiSlice";
import { useMarkerStore } from "@/store/markerSlice";
import { VideoPlayer } from "./VideoPlayer";
import { TimelineView } from "@/components/Timeline/TimelineView";
import { MarkerPanel } from "@/components/Markers/MarkerPanel";
import { ClipPanel } from "@/components/Clips/ClipPanel";
import { AutoClipPanel } from "@/components/AutoClips/AutoClipPanel";
import { ExportDialog } from "@/components/Export/ExportDialog";
import { useKeyboard } from "@/hooks/useKeyboard";
import { generateId } from "@/utils";
import type { AutoClipDraft, AutoClipMode, AutoClipSegment, EditorTab } from "@/types";

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
  const [autoDraft, setAutoDraft] = useState<AutoClipDraft | null>(null);

  const project = projects.find((p) => p.id === currentProjectId);
  if (!project) return null;

  const tabs: { key: EditorTab; label: string }[] = [
    { key: "markers", label: "标记" },
    { key: "clips", label: "片段" },
    { key: "auto", label: "自动" },
    { key: "info", label: "信息" },
  ];

  const visibleAutoSegments = useMemo(
    () => autoDraft?.segments ?? [],
    [autoDraft]
  );

  const runAutoClipDraft = (mode: AutoClipMode) => {
    const duration = project.sourceVideo?.durationSec ?? 0;
    setSelectedTab("auto");
    setAutoDraft({
      status: "running",
      mode,
      progress: 0.35,
      segments: [],
      createdAt: new Date().toISOString(),
    });

    window.setTimeout(() => {
      setAutoDraft({
        status: "completed",
        mode,
        progress: 1,
        segments: createLocalAutoSegments(duration, mode),
        createdAt: new Date().toISOString(),
      });
    }, 250);
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
            onClick={() => runAutoClipDraft(autoDraft?.mode ?? "balanced")}
            className="px-3 py-1 text-sm rounded-md border hover:bg-accent"
            disabled={!project.sourceVideo}
          >
            自动剪辑
          </button>
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
        autoSegments={visibleAutoSegments}
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

function createLocalAutoSegments(duration: number, mode: AutoClipMode): AutoClipSegment[] {
  if (duration <= 0) return [];
  const settings: Record<AutoClipMode, { keep: number; cut: number; pre: number; post: number }> = {
    conservative: { keep: 18, cut: 7, pre: 3, post: 4 },
    balanced: { keep: 16, cut: 9, pre: 2, post: 3 },
    aggressive: { keep: 13, cut: 12, pre: 1, post: 2 },
  };
  const preset = settings[mode];
  const keepRanges: Array<[number, number]> = [];
  let cursor = Math.min(2, duration);

  while (cursor < duration) {
    const start = Math.max(0, cursor - preset.pre);
    const end = Math.min(duration, cursor + preset.keep + preset.post);
    if (end - start >= 4) keepRanges.push([start, end]);
    cursor += preset.keep + preset.cut;
  }

  const merged = mergeRanges(keepRanges, mode === "conservative" ? 3 : 2);
  const segments: AutoClipSegment[] = [];
  let timelineCursor = 0;
  merged.forEach(([start, end], index) => {
    if (start > timelineCursor) {
      segments.push(createAutoSegment(timelineCursor, start, "cut", 0.7, ["low_activity"]));
    }
    segments.push(createAutoSegment(start, end, "keep", 0.76 + (index % 3) * 0.06, ["high_motion", "sustained_activity"]));
    timelineCursor = Math.max(timelineCursor, end);
  });
  if (timelineCursor < duration) {
    segments.push(createAutoSegment(timelineCursor, duration, "cut", 0.7, ["low_activity"]));
  }
  return segments.filter((segment) => segment.endSec > segment.startSec);
}

function createAutoSegment(
  startSec: number,
  endSec: number,
  state: AutoClipSegment["state"],
  confidence: number,
  reason: string[]
): AutoClipSegment {
  return {
    id: generateId(),
    startSec: roundTime(startSec),
    endSec: roundTime(endSec),
    confidence: Math.min(0.96, confidence),
    reason,
    source: "auto",
    state,
  };
}

function mergeRanges(ranges: Array<[number, number]>, mergeGap: number): Array<[number, number]> {
  return ranges.reduce<Array<[number, number]>>((acc, range) => {
    const previous = acc[acc.length - 1];
    if (previous && range[0] - previous[1] <= mergeGap) {
      previous[1] = Math.max(previous[1], range[1]);
    } else {
      acc.push([...range]);
    }
    return acc;
  }, []);
}

function roundTime(value: number): number {
  return Math.round(value * 100) / 100;
}

function formatTimePrecise(seconds: number): string {
  const ts = Math.floor(seconds);
  const m = Math.floor(ts / 60);
  const s = ts % 60;
  const cs = Math.floor((seconds - ts) * 100);
  return `${m}:${String(s).padStart(2, "0")}.${String(cs).padStart(2, "0")}`;
}
