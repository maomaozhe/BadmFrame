import { create } from "zustand";
import type { Project } from "@/types";
import { db } from "@/services/db";
import { api } from "@/services/api";
import { generateId } from "@/utils";

interface ProjectSlice {
  projects: Project[];
  currentProjectId: string | null;
  loading: boolean;
  loadProjects: () => Promise<void>;
  createProject: (name: string) => Promise<Project>;
  deleteProject: (id: string) => Promise<void>;
  setCurrentProject: (id: string | null) => void;
  getCurrentProject: () => Project | undefined;
  updateProject: (id: string, updates: Partial<Project>) => Promise<void>;
  upsertProject: (project: Project) => Promise<void>;
}

export const useProjectStore = create<ProjectSlice>((set, get) => ({
  projects: [],
  currentProjectId: null,
  loading: false,

  async loadProjects() {
    set({ loading: true });
    try {
      const projects = await api.listProjects();
      await Promise.all(projects.map((project) => db.saveProject(_mergeLocalPlayback(project, get().projects))));
      set({ projects: projects.map((project) => _mergeLocalPlayback(project, get().projects)), loading: false });
    } catch {
      const projects = await db.getAllProjects();
      set({ projects, loading: false });
    }
  },

  async createProject(name: string) {
    const now = new Date().toISOString();
    const project: Project = {
      id: generateId(),
      name,
      sourceVideo: null,
      markers: [],
      clips: [],
      createdAt: now,
      updatedAt: now,
    };
    await db.saveProject(project);
    set((s) => ({ projects: [project, ...s.projects] }));
    return project;
  },

  async deleteProject(id: string) {
    try {
      await api.deleteProject(id);
    } catch {
      // Local-only fallback projects can still be removed from IndexedDB.
    }
    await db.deleteProject(id);
    set((s) => ({
      projects: s.projects.filter((p) => p.id !== id),
      currentProjectId: s.currentProjectId === id ? null : s.currentProjectId,
    }));
  },

  setCurrentProject(id) {
    set({ currentProjectId: id });
  },

  getCurrentProject() {
    const { projects, currentProjectId } = get();
    return projects.find((p) => p.id === currentProjectId);
  },

  async updateProject(id, updates) {
    set((s) => ({
      projects: s.projects.map((p) =>
        p.id === id ? { ...p, ...updates, updatedAt: new Date().toISOString() } : p
      ),
    }));
    const project = get().projects.find((p) => p.id === id);
    if (!project) return;
    // 保存到 IndexedDB 前清除 volatile 的 objectURL（blob: URL 在刷新后失效）
    const toSave = { ...project };
    if (toSave.sourceVideo?.objectURL) {
      toSave.sourceVideo = { ...toSave.sourceVideo, objectURL: undefined };
    }
    await db.saveProject(toSave);
  },

  async upsertProject(project) {
    await db.saveProject(project);
    set((s) => ({
      projects: [project, ...s.projects.filter((p) => p.id !== project.id)],
    }));
  },
}));

function _mergeLocalPlayback(project: Project, previous: Project[]): Project {
  const local = previous.find((item) => item.id === project.id);
  if (!local?.sourceVideo?.objectURL || !project.sourceVideo) return project;
  return {
    ...project,
    sourceVideo: {
      ...project.sourceVideo,
      objectURL: local.sourceVideo.objectURL,
    },
  };
}
