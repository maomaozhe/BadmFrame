import { create } from "zustand";
import type { Project } from "@/types";
import { db } from "@/services/db";
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
}

export const useProjectStore = create<ProjectSlice>((set, get) => ({
  projects: [],
  currentProjectId: null,
  loading: false,

  async loadProjects() {
    set({ loading: true });
    const projects = await db.getAllProjects();
    set({ projects, loading: false });
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
    if (project) await db.saveProject(project);
  },
}));
