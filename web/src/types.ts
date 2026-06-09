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
  projectId?: string | null;
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
  taskId?: string;
  stage?: string;
  message?: string;
  error?: string;
  createdAt?: string;
}

export type RallyReviewState = "pending" | "accepted" | "rejected" | "adjusted";
export type RallySource = "model" | "imported-json" | "manual";

export interface RallyCandidate {
  id: string;
  startSec: number;
  endSec: number;
  confidence: number;
  reviewState: RallyReviewState;
  startReason: string[];
  endReason: string[];
  source: RallySource;
  trajectoryStats?: {
    visibleRatio?: number;
    maxGapSec?: number;
    directionChanges?: number;
    meanSpeedPxSec?: number;
  };
}

export interface RallyAnalysisResult {
  taskId: string;
  videoId: string;
  projectId?: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  durationSec: number;
  candidates: RallyCandidate[];
  error?: string;
}

export type EditorTab = "markers" | "clips" | "rallies" | "info";

export type ExportSortMode = "position" | "duration";

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
