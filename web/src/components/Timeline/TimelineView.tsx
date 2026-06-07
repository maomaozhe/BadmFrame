import { useRef, useState, useEffect } from "react";
import { useVideoStore } from "@/store/videoSlice";
import { formatTime, formatTimePrecise } from "@/utils";
import type { AutoClipSegment, Marker, RallyCandidate } from "@/types";

interface Props {
  duration: number;
  markers: Marker[];
  autoSegments?: AutoClipSegment[];
  rallyCandidates?: RallyCandidate[];
  selectedRallyId?: string | null;
  onSelectRally?: (id: string) => void;
  onAddMarker: () => void;
}

export function TimelineView({
  duration,
  markers,
  autoSegments = [],
  rallyCandidates = [],
  selectedRallyId = null,
  onSelectRally,
  onAddMarker,
}: Props) {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [pixelsPerSecond, setPixelsPerSecond] = useState(10);
  const [scrollLeft, setScrollLeft] = useState(0);
  const currentTime = useVideoStore((s) => s.currentTime);

  const totalWidth = duration * pixelsPerSecond;
  const zoomIn = () => setPixelsPerSecond((p) => Math.min(100, p * 1.5));
  const zoomOut = () => setPixelsPerSecond((p) => Math.max(2, p / 1.5));

  const interval = calcInterval(pixelsPerSecond);

  const handleScroll = () => {
    const el = timelineRef.current;
    if (el) setScrollLeft(el.scrollLeft);
  };

  useEffect(() => {
    const el = timelineRef.current;
    if (el) {
      el.scrollLeft = Math.max(0, currentTime * pixelsPerSecond - el.clientWidth / 2);
    }
  }, [currentTime, pixelsPerSecond]);

  const seekTo = (t: number) => {
    const video = document.querySelector("video");
    if (video) video.currentTime = t;
  };

  const onTimelineClick = (e: React.MouseEvent) => {
    const rect = timelineRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left + scrollLeft;
    const t = (x) / pixelsPerSecond;
    seekTo(Math.max(0, Math.min(t, duration)));
  };

  return (
    <div className="border-b shrink-0">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b">
        <button
          onClick={onAddMarker}
          className="px-2 py-0.5 text-xs rounded border hover:bg-accent"
          title="添加标记 (M)"
        >
          📌 标记
        </button>
        <button onClick={zoomOut} className="px-2 text-xs border rounded hover:bg-accent">−</button>
        <button onClick={zoomIn} className="px-2 text-xs border rounded hover:bg-accent">+</button>
        <span className="text-xs text-muted-foreground ml-auto font-mono">
          {formatTimePrecise(currentTime)}
        </span>
      </div>

      {/* Timeline canvas */}
      <div ref={timelineRef} className="overflow-x-auto" onScroll={handleScroll} style={{ height: 68 }}>
        <div className="relative" style={{ width: Math.max(totalWidth + 16, 16), height: 68 }}>
          {/* Ruler */}
          <svg className="absolute top-0 left-0" width={totalWidth + 16} height={20}>
            {Array.from({ length: Math.ceil(duration / interval) + 1 }).map((_, i) => {
              const sec = i * interval;
              if (sec > duration) return null;
              const x = sec * pixelsPerSecond;
              const major = i % Math.max(Math.round(interval * 4 / interval), 1) === 0;
              return (
                <g key={i}>
                  <line x1={x} y1={2} x2={x} y2={major ? 18 : 10}
                    stroke={major ? "#888" : "#ccc"} strokeWidth={major ? 1 : 0.5} />
                  {major && (
                    <text x={x} y={10} fontSize={8} fill="#999" textAnchor="middle">
                      {formatTime(sec)}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Thumbnail strip background */}
          <div className="absolute top-5 left-0 h-9 w-full bg-muted/20" />

          {/* Auto clip draft overlay */}
          <div className="absolute top-5 left-0 h-9 w-full pointer-events-none">
            {autoSegments.map((segment) => {
              const left = segment.startSec * pixelsPerSecond;
              const width = Math.max(1, (segment.endSec - segment.startSec) * pixelsPerSecond);
              const color = segment.state === "keep" ? "bg-emerald-500/25" : "bg-zinc-500/20";
              const border = segment.state === "keep" ? "border-emerald-500/60" : "border-zinc-400/50";
              return (
                <div
                  key={segment.id}
                  className={`absolute top-1 h-7 border ${color} ${border}`}
                  style={{ left, width }}
                />
              );
            })}
          </div>

          {/* Rally candidate overlay */}
          <div className="absolute top-5 left-0 h-9 w-full">
            {rallyCandidates.map((candidate) => {
              const left = candidate.startSec * pixelsPerSecond;
              const width = Math.max(1, (candidate.endSec - candidate.startSec) * pixelsPerSecond);
              const selected = candidate.id === selectedRallyId;
              return (
                <button
                  key={candidate.id}
                  className={`absolute top-1 z-20 h-7 border transition-colors ${rallyClass(candidate, selected)}`}
                  style={{ left, width }}
                  title={`${formatTimePrecise(candidate.startSec)} - ${formatTimePrecise(candidate.endSec)}`}
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelectRally?.(candidate.id);
                    seekTo(candidate.startSec);
                  }}
                />
              );
            })}
          </div>

          {/* Marker diamonds */}
          <svg className="absolute top-5 left-0" width={totalWidth + 16} height={44}>
            {markers.sort((a, b) => a.timestampSec - b.timestampSec).map((m) => {
              const x = m.timestampSec * pixelsPerSecond;
              const hex = markerColorHex(m.color);
              return (
                <g key={m.id} className="cursor-pointer" onClick={() => seekTo(m.timestampSec)}>
                  <polygon points={`${x},4 ${x - 5},12 ${x},18 ${x + 5},12`} fill={hex} />
                </g>
              );
            })}
          </svg>

          {/* Playhead */}
          <div className="absolute top-5 left-0 w-0.5 bg-red-500 z-10 pointer-events-none"
            style={{ height: 44, left: currentTime * pixelsPerSecond }} />

          {/* Click area */}
          <div className="absolute top-5 left-0 z-0 w-full h-11 cursor-pointer" onClick={onTimelineClick} />
        </div>
      </div>
    </div>
  );
}

function calcInterval(pps: number): number {
  if (pps >= 40) return 1;
  if (pps >= 15) return 2;
  if (pps >= 8) return 5;
  if (pps >= 4) return 10;
  if (pps >= 2) return 30;
  return 60;
}

function markerColorHex(c: string): string {
  const m: Record<string, string> = {
    yellow: "#eab308", red: "#ef4444", blue: "#3b82f6",
    green: "#22c55e", orange: "#f97316", purple: "#a855f7",
  };
  return m[c] ?? "#eab308";
}

function rallyClass(candidate: RallyCandidate, selected: boolean): string {
  const stateClass =
    candidate.reviewState === "accepted" || candidate.reviewState === "adjusted"
      ? "bg-emerald-500/25 border-emerald-500/70"
      : candidate.reviewState === "rejected"
        ? "bg-zinc-400/15 border-zinc-400/40 opacity-60"
        : "bg-amber-500/20 border-amber-500/60";
  return selected ? `${stateClass} ring-2 ring-primary ring-offset-1` : stateClass;
}
