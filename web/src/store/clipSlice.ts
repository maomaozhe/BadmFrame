import { create } from "zustand";
import type { AutoClipSegment, Clip, ClipExportStatus, RallyCandidate } from "@/types";
import { useProjectStore } from "./projectSlice";
import { api } from "@/services/api";
import { generateId } from "@/utils";

interface ClipSlice {
  createClip: (startTimeSec: number, endTimeSec: number, label?: string, anchorMarkerId?: string) => void;
  createClipFromMarker: (markerTimestamp: number, duration: number) => void;
  createClipsFromAutoSegments: (segments: AutoClipSegment[]) => void;
  createClipsFromRallyCandidates: (candidates: RallyCandidate[]) => void;
  deleteClip: (clipId: string) => void;
  updateClip: (clipId: string, updates: Partial<Pick<Clip, "startTimeSec" | "endTimeSec" | "label" | "notes">>) => void;
  updateExportStatus: (clipId: string, status: ClipExportStatus, filePath?: string) => void;
  getClips: () => Clip[];
}

const AUTO_SOURCE = "auto-dead-time";

export const useClipStore = create<ClipSlice>(() => ({
  createClip: (startTimeSec, endTimeSec, label = "", anchorMarkerId) => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;

    const clip: Clip = {
      id: generateId(),
      startTimeSec,
      endTimeSec,
      label,
      notes: "",
      anchorMarkerId,
      exportStatus: "none",
      createdAt: new Date().toISOString(),
    };
    updateProject(currentProjectId, { clips: [...project.clips, clip] });
    api.createClip(currentProjectId, clip)
      .then((saved) => {
        const latest = useProjectStore.getState().projects.find((p) => p.id === currentProjectId);
        if (!latest) return;
        updateProject(currentProjectId, {
          clips: latest.clips.map((c) => (c.id === clip.id ? saved : c)),
        });
      })
      .catch(() => {});
  },

  createClipFromMarker: (markerTimestamp, duration) => {
    const start = Math.max(0, markerTimestamp - 3);
    const end = Math.min(duration, markerTimestamp + 7);
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;

    const clip: Clip = {
      id: generateId(),
      startTimeSec: start,
      endTimeSec: end,
      label: "片段",
      notes: "",
      anchorMarkerId: undefined,
      exportStatus: "none",
      createdAt: new Date().toISOString(),
    };
    updateProject(currentProjectId, { clips: [...project.clips, clip] });
    api.createClip(currentProjectId, clip)
      .then((saved) => {
        const latest = useProjectStore.getState().projects.find((p) => p.id === currentProjectId);
        if (!latest) return;
        updateProject(currentProjectId, {
          clips: latest.clips.map((c) => (c.id === clip.id ? saved : c)),
        });
      })
      .catch(() => {});
  },

  createClipsFromAutoSegments: (segments) => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return [];
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return [];

    const now = new Date().toISOString();
    const autoClips: Clip[] = segments
      .filter((segment) => segment.state === "keep" && segment.endSec > segment.startSec)
      .sort((a, b) => a.startSec - b.startSec)
      .map((segment, index) => ({
        id: generateId(),
        startTimeSec: segment.startSec,
        endTimeSec: segment.endSec,
        label: `自动回合 ${index + 1}`,
        notes: `source:${AUTO_SOURCE} confidence:${segment.confidence.toFixed(2)} reason:${segment.reason.join(",")}`,
        anchorMarkerId: undefined,
        exportStatus: "none" as ClipExportStatus,
        createdAt: now,
      }));

    updateProject(currentProjectId, { clips: [...project.clips, ...autoClips] });
    return autoClips.map((c) => c.id);
  },

  removeAutoClips: () => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;
    updateProject(currentProjectId, {
      clips: project.clips.filter((c) => !c.notes.startsWith(`source:${AUTO_SOURCE}`)),
    });
  },

  createClipsFromRallyCandidates: (candidates) => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;

    const now = new Date().toISOString();
    const rallyClips: Clip[] = candidates
      .filter((candidate) =>
        (candidate.reviewState === "accepted" || candidate.reviewState === "adjusted") &&
        candidate.endSec > candidate.startSec
      )
      .sort((a, b) => a.startSec - b.startSec)
      .map((candidate, index) => ({
        id: generateId(),
        startTimeSec: candidate.startSec,
        endTimeSec: candidate.endSec,
        label: `有效回合 ${index + 1}`,
        notes: `source:rally-candidate candidate:${candidate.id} confidence:${candidate.confidence.toFixed(2)} state:${candidate.reviewState}`,
        anchorMarkerId: undefined,
        exportStatus: "none",
        createdAt: now,
      }));

    updateProject(currentProjectId, { clips: [...project.clips, ...rallyClips] });
  },

  deleteClip: (clipId) => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;
    updateProject(currentProjectId, {
      clips: project.clips.filter((c) => c.id !== clipId),
    });
    api.deleteClip(currentProjectId, clipId).catch(() => {});
  },

  updateClip: (clipId, updates) => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;
    updateProject(currentProjectId, {
      clips: project.clips.map((c) =>
        c.id === clipId ? { ...c, ...updates } : c
      ),
    });
    api.updateClip(currentProjectId, clipId, updates).catch(() => {});
  },

  updateExportStatus: (clipId, status, filePath) => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;
    updateProject(currentProjectId, {
      clips: project.clips.map((c) =>
        c.id === clipId
          ? { ...c, exportStatus: status, ...(filePath ? { exportedFilePath: filePath } : {}) }
          : c
      ),
    });
  },

  getClips: () => {
    const { currentProjectId, projects } = useProjectStore.getState();
    const project = projects.find((p) => p.id === currentProjectId);
    return project?.clips ?? [];
  },
}));
