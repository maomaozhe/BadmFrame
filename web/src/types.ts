export interface Project {
  id: string;
  serverProjectId?: string;
  name: string;
  sourceVideo: SourceVideo | null;
  markers: Marker[];
  clips: Clip[];
  createdAt: string;
  updatedAt: string;
}

export interface SourceVideo {
  id: string;
  serverVideoId?: string;
  fileName: string;
  filePath: string;
  durationSec: number;
  width: number;
  height: number;
  frameRate: number;
  codec: string;
  isVFR: boolean;
  fileSize: number;
  importDate: string;
  objectURL?: string;
}

export interface Marker {
  id: string;
  timestampSec: number;
  label: string;
  color: MarkerColor;
  createdAt: string;
}

export type MarkerColor = "yellow" | "red" | "blue" | "green" | "orange" | "purple";

export const MARKER_COLORS: { key: MarkerColor; label: string; hex: string }[] = [
  { key: "yellow", label: "黄色", hex: "#eab308" },
  { key: "red", label: "红色", hex: "#ef4444" },
  { key: "blue", label: "蓝色", hex: "#3b82f6" },
  { key: "green", label: "绿色", hex: "#22c55e" },
  { key: "orange", label: "橙色", hex: "#f97316" },
  { key: "purple", label: "紫色", hex: "#a855f7" },
];

export interface Clip {
  id: string;
  startTimeSec: number;
  endTimeSec: number;
  label: string;
  notes: string;
  anchorMarkerId?: string;
  exportStatus: ClipExportStatus;
  exportedFilePath?: string;
  createdAt: string;
}

export type ClipExportStatus = "none" | "exporting" | "completed" | "failed";

export type AutoClipMode = "conservative" | "balanced" | "aggressive";
export type AutoClipSegmentState = "keep" | "cut";

export interface AutoClipSegment {
  id: string;
  startSec: number;
  endSec: number;
  confidence: number;
  reason: string[];
  source: "auto";
  state: AutoClipSegmentState;
}

export interface AutoClipDraft {
  taskId?: string;
  status: "idle" | "running" | "completed" | "failed";
  mode: AutoClipMode;
  progress: number;
  segments: AutoClipSegment[];
  error?: string;
  createdAt?: string;
}

export type EditorTab = "markers" | "clips" | "auto" | "info";

export interface ExportJob {
  taskId: string;
  status: "queued" | "running" | "completed" | "failed";
  mode: "separate" | "merged";
  preset: "auto" | "fast_copy" | "compatible";
  results: Array<{ id: string; status: string; path?: string; error?: string }>;
  error?: string | null;
  createdAt?: string;
  completedAt?: string | null;
}
