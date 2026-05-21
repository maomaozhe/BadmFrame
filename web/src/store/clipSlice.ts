import { create } from "zustand";
import type { Clip, ClipExportStatus } from "@/types";
import { useProjectStore } from "./projectSlice";
import { generateId } from "@/utils";

interface ClipSlice {
  createClip: (startTimeSec: number, endTimeSec: number, label?: string, anchorMarkerId?: string) => void;
  createClipFromMarker: (markerTimestamp: number, duration: number) => void;
  deleteClip: (clipId: string) => void;
  updateClip: (clipId: string, updates: Partial<Pick<Clip, "startTimeSec" | "endTimeSec" | "label" | "notes">>) => void;
  updateExportStatus: (clipId: string, status: ClipExportStatus, filePath?: string) => void;
  getClips: () => Clip[];
}

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
  },

  deleteClip: (clipId) => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;
    updateProject(currentProjectId, {
      clips: project.clips.filter((c) => c.id !== clipId),
    });
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
