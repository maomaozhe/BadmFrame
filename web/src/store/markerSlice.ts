import { create } from "zustand";
import type { Marker, MarkerColor } from "@/types";
import { useProjectStore } from "./projectSlice";
import { api } from "@/services/api";
import { generateId } from "@/utils";

interface MarkerSlice {
  addMarker: (timestampSec: number, label?: string, color?: MarkerColor) => void;
  deleteMarker: (markerId: string) => void;
  updateMarker: (markerId: string, updates: Partial<Pick<Marker, "label" | "color">>) => void;
  getMarkers: () => Marker[];
}

export const useMarkerStore = create<MarkerSlice>(() => ({
  addMarker: (timestampSec, label = "", color = "yellow") => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;

    const marker: Marker = {
      id: generateId(),
      timestampSec,
      label,
      color,
      createdAt: new Date().toISOString(),
    };
    const updated = { markers: [...project.markers, marker] };
    updateProject(currentProjectId, updated);
    api.createMarker(currentProjectId, { timestampSec, label, color })
      .then((saved) => {
        const latest = useProjectStore.getState().projects.find((p) => p.id === currentProjectId);
        if (!latest) return;
        updateProject(currentProjectId, {
          markers: latest.markers.map((m) => (m.id === marker.id ? saved : m)),
        });
      })
      .catch(() => {});
  },

  deleteMarker: (markerId) => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;
    updateProject(currentProjectId, {
      markers: project.markers.filter((m) => m.id !== markerId),
    });
    api.deleteMarker(currentProjectId, markerId).catch(() => {});
  },

  updateMarker: (markerId, updates) => {
    const { currentProjectId, projects, updateProject } = useProjectStore.getState();
    if (!currentProjectId) return;
    const project = projects.find((p) => p.id === currentProjectId);
    if (!project) return;
    updateProject(currentProjectId, {
      markers: project.markers.map((m) =>
        m.id === markerId ? { ...m, ...updates } : m
      ),
    });
    api.updateMarker(currentProjectId, markerId, updates).catch(() => {});
  },

  getMarkers: () => {
    const { currentProjectId, projects } = useProjectStore.getState();
    const project = projects.find((p) => p.id === currentProjectId);
    return project?.markers ?? [];
  },
}));
