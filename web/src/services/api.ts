import type {
  AutoClipDraft,
  AutoClipMode,
  AutoClipSegment,
  Clip,
  ExportJob,
  Marker,
  MarkerColor,
  Project,
  SourceVideo,
} from "@/types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: init?.body instanceof FormData
      ? init.headers
      : { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`;
    try {
      const body = await resp.json();
      detail = body.detail || detail;
    } catch {
      // keep HTTP status fallback
    }
    throw new Error(detail);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

type ApiProject = {
  id: string;
  name: string;
  source_video: ApiSourceVideo | null;
  markers: ApiMarker[];
  clips: ApiClip[];
  created_at: string;
  updated_at: string;
};

type ApiSourceVideo = {
  id: string;
  file_name: string;
  file_path: string;
  duration_sec: number;
  width: number;
  height: number;
  frame_rate: number;
  codec: string;
  is_vfr: boolean;
  file_size: number;
  import_date: string;
};

type ApiMarker = {
  id: string;
  timestamp_sec: number;
  label: string;
  color: MarkerColor;
  created_at: string;
};

type ApiClip = {
  id: string;
  start_time_sec: number;
  end_time_sec: number;
  label: string;
  notes: string;
  anchor_marker_id?: string | null;
  export_status: Clip["exportStatus"];
  exported_file_path?: string | null;
  created_at: string;
};

type ApiAnalysisJob = {
  task_id: string;
  video_id: string;
  project_id: string | null;
  status: AutoClipDraft["status"];
  params: { mode: AutoClipMode };
  progress: number;
  duration_sec: number;
  keep_segments: number;
  cut_segments: number;
  error?: string | null;
  created_at: string;
  completed_at?: string | null;
};

type ApiAnalysisResult = {
  task_id: string;
  status: AutoClipDraft["status"];
  params: { mode: AutoClipMode };
  progress: number;
  segments: Array<{
    start_sec: number;
    end_sec: number;
    confidence: number;
    reason: string[];
    source: "auto";
    state: "keep" | "cut";
  }>;
  error?: string | null;
};

type ApiExportJob = {
  task_id: string;
  status: ExportJob["status"];
  mode: ExportJob["mode"];
  preset: ExportJob["preset"];
  results: ExportJob["results"];
  error?: string | null;
  created_at?: string;
  completed_at?: string | null;
};

export const api = {
  async listProjects(): Promise<Project[]> {
    return (await request<ApiProject[]>("/projects")).map(toProject);
  },

  async uploadVideo(file: File): Promise<SourceVideo> {
    const data = new FormData();
    data.append("file", file);
    return toSourceVideo(await request<ApiSourceVideo>("/videos/upload", { method: "POST", body: data }));
  },

  async createProject(name: string, videoId?: string): Promise<Project> {
    return toProject(await request<ApiProject>("/projects", {
      method: "POST",
      body: JSON.stringify({ name, video_id: videoId }),
    }));
  },

  async deleteProject(projectId: string): Promise<void> {
    await request<void>(`/projects/${projectId}`, { method: "DELETE" });
  },

  async createMarker(projectId: string, marker: Pick<Marker, "timestampSec" | "label" | "color">): Promise<Marker> {
    return toMarker(await request<ApiMarker>(`/projects/${projectId}/markers`, {
      method: "POST",
      body: JSON.stringify({
        timestamp_sec: marker.timestampSec,
        label: marker.label,
        color: marker.color,
      }),
    }));
  },

  async updateMarker(projectId: string, markerId: string, updates: Partial<Pick<Marker, "label" | "color">>): Promise<Marker> {
    return toMarker(await request<ApiMarker>(`/projects/${projectId}/markers/${markerId}`, {
      method: "PUT",
      body: JSON.stringify(updates),
    }));
  },

  async deleteMarker(projectId: string, markerId: string): Promise<void> {
    await request<void>(`/projects/${projectId}/markers/${markerId}`, { method: "DELETE" });
  },

  async createClip(projectId: string, clip: Pick<Clip, "startTimeSec" | "endTimeSec" | "label" | "notes" | "anchorMarkerId">): Promise<Clip> {
    return toClip(await request<ApiClip>(`/projects/${projectId}/clips`, {
      method: "POST",
      body: JSON.stringify({
        start_time_sec: clip.startTimeSec,
        end_time_sec: clip.endTimeSec,
        label: clip.label,
        notes: clip.notes,
        anchor_marker_id: clip.anchorMarkerId,
      }),
    }));
  },

  async updateClip(projectId: string, clipId: string, updates: Partial<Pick<Clip, "startTimeSec" | "endTimeSec" | "label" | "notes">>): Promise<Clip> {
    return toClip(await request<ApiClip>(`/projects/${projectId}/clips/${clipId}`, {
      method: "PUT",
      body: JSON.stringify({
        start_time_sec: updates.startTimeSec,
        end_time_sec: updates.endTimeSec,
        label: updates.label,
        notes: updates.notes,
      }),
    }));
  },

  async deleteClip(projectId: string, clipId: string): Promise<void> {
    await request<void>(`/projects/${projectId}/clips/${clipId}`, { method: "DELETE" });
  },

  async startAnalysis(videoId: string, mode: AutoClipMode): Promise<{ task_id: string; status: string }> {
    return request(`/videos/${videoId}/analysis`, { method: "POST", body: JSON.stringify({ mode }) });
  },

  async getAnalysis(videoId: string, taskId: string): Promise<AutoClipDraft> {
    return toAutoDraft(await request<ApiAnalysisResult>(`/videos/${videoId}/analysis/${taskId}`));
  },

  async getLatestAnalysis(projectId: string): Promise<ApiAnalysisJob | null> {
    try {
      return await request<ApiAnalysisJob>(`/projects/${projectId}/analysis/latest`);
    } catch {
      return null;
    }
  },

  async applyAutoClips(projectId: string, taskId: string): Promise<{ created_clip_ids: string[]; clips_created: number }> {
    return request(`/projects/${projectId}/auto-clips/apply`, {
      method: "POST",
      body: JSON.stringify({ task_id: taskId, replace_existing_auto: true }),
    });
  },

  async submitExport(projectId: string, clipIds: string[], mode: ExportJob["mode"]): Promise<ExportJob> {
    return toExportJob(await request<ApiExportJob>("/exports", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, clip_ids: clipIds, mode, preset: "auto" }),
    }));
  },

  async getExport(taskId: string): Promise<ExportJob> {
    return toExportJob(await request<ApiExportJob>(`/exports/${taskId}`));
  },

  async listExports(projectId: string): Promise<ExportJob[]> {
    return (await request<ApiExportJob[]>(`/projects/${projectId}/exports`)).map(toExportJob);
  },
};

export function toProject(p: ApiProject): Project {
  return {
    id: p.id,
    serverProjectId: p.id,
    name: p.name,
    sourceVideo: p.source_video ? toSourceVideo(p.source_video) : null,
    markers: (p.markers || []).map(toMarker),
    clips: (p.clips || []).map(toClip),
    createdAt: p.created_at,
    updatedAt: p.updated_at,
  };
}

function toSourceVideo(v: ApiSourceVideo): SourceVideo {
  return {
    id: v.id,
    serverVideoId: v.id,
    fileName: v.file_name,
    filePath: v.file_path,
    durationSec: v.duration_sec,
    width: v.width,
    height: v.height,
    frameRate: v.frame_rate,
    codec: v.codec,
    isVFR: v.is_vfr,
    fileSize: v.file_size,
    importDate: v.import_date,
    objectURL: `/storage/uploads/${encodeURIComponent(v.file_name)}`,
  };
}

function toMarker(m: ApiMarker): Marker {
  return {
    id: m.id,
    timestampSec: m.timestamp_sec,
    label: m.label,
    color: m.color,
    createdAt: m.created_at,
  };
}

function toClip(c: ApiClip): Clip {
  return {
    id: c.id,
    startTimeSec: c.start_time_sec,
    endTimeSec: c.end_time_sec,
    label: c.label,
    notes: c.notes,
    anchorMarkerId: c.anchor_marker_id || undefined,
    exportStatus: c.export_status,
    exportedFilePath: c.exported_file_path || undefined,
    createdAt: c.created_at,
  };
}

function toAutoDraft(result: ApiAnalysisResult): AutoClipDraft {
  return {
    taskId: result.task_id,
    status: result.status,
    mode: result.params.mode,
    progress: result.progress,
    segments: result.segments.map((segment, index): AutoClipSegment => ({
      id: `${result.task_id}-${index}`,
      startSec: segment.start_sec,
      endSec: segment.end_sec,
      confidence: segment.confidence,
      reason: segment.reason,
      source: "auto",
      state: segment.state,
    })),
    error: result.error || undefined,
    createdAt: new Date().toISOString(),
  };
}

function toExportJob(job: ApiExportJob): ExportJob {
  return {
    taskId: job.task_id,
    status: job.status,
    mode: job.mode,
    preset: job.preset,
    results: job.results || [],
    error: job.error,
    createdAt: job.created_at,
    completedAt: job.completed_at,
  };
}
