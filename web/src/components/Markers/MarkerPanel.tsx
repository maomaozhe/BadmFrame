import { useState } from "react";
import { useMarkerStore } from "@/store/markerSlice";
import { useClipStore } from "@/store/clipSlice";
import { useVideoStore } from "@/store/videoSlice";
import { Input } from "@/components/ui/input";
import { formatTimePrecise } from "@/utils";
import { MARKER_COLORS, type Marker } from "@/types";

interface Props {
  markers: Marker[];
}

export function MarkerPanel({ markers }: Props) {
  const { deleteMarker, updateMarker } = useMarkerStore();
  const { createClipFromMarker } = useClipStore();
  const duration = useVideoStore((s) => s.duration);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  const seekTo = (t: number) => {
    const video = document.querySelector("video");
    if (video) video.currentTime = t;
  };

  if (markers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground gap-2 py-12">
        <span className="text-3xl">📍</span>
        <p className="text-sm">还没有标记点</p>
        <p className="text-xs">播放视频时点击标记按钮或按 M 键添加标记</p>
      </div>
    );
  }

  const sorted = [...markers].sort((a, b) => a.timestampSec - b.timestampSec);

  return (
    <div className="divide-y">
      {sorted.map((m) => {
        const colorInfo = MARKER_COLORS.find((c) => c.key === m.color);
        return (
          <div key={m.id} className="px-3 py-1.5 flex items-center gap-2 hover:bg-accent/50 group">
            <div
              className="w-2.5 h-2.5 rounded-full shrink-0 cursor-pointer"
              style={{ backgroundColor: colorInfo?.hex }}
              onClick={() => seekTo(m.timestampSec)}
            />
            <div className="flex-1 min-w-0 cursor-pointer" onClick={() => seekTo(m.timestampSec)}>
              {editingId === m.id ? (
                <Input
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  onBlur={() => { if (editText.trim()) updateMarker(m.id, { label: editText.trim() }); setEditingId(null); }}
                  onKeyDown={(e) => { if (e.key === "Enter") { if (editText.trim()) updateMarker(m.id, { label: editText.trim() }); setEditingId(null); } }}
                  className="h-6 text-sm"
                  autoFocus
                />
              ) : (
                <p className="text-sm truncate">{m.label || "未命名标记"}</p>
              )}
              <p className="text-xs text-muted-foreground font-mono">{formatTimePrecise(m.timestampSec)}</p>
            </div>
            <div className="hidden group-hover:flex items-center gap-0.5">
              <button className="text-xs px-1.5 py-0.5 rounded hover:bg-accent" onClick={() => { setEditingId(m.id); setEditText(m.label); }}>✏️</button>
              <button className="text-xs px-1.5 py-0.5 rounded hover:bg-accent" onClick={() => createClipFromMarker(m.timestampSec, duration)}>✂️</button>
              <select value={m.color} onChange={(e) => updateMarker(m.id, { color: e.target.value as any })} className="text-xs border rounded bg-transparent">
                {MARKER_COLORS.map((c) => (<option key={c.key} value={c.key}>{c.label}</option>))}
              </select>
              <button className="text-xs px-1.5 py-0.5 rounded hover:bg-destructive/10 text-destructive" onClick={() => deleteMarker(m.id)}>🗑</button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
