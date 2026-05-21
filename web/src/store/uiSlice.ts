import { create } from "zustand";
import type { EditorTab } from "@/types";

interface UISlice {
  selectedTab: EditorTab;
  showImport: boolean;
  showExport: boolean;
  errorMessage: string | null;

  setSelectedTab: (tab: EditorTab) => void;
  setShowImport: (v: boolean) => void;
  setShowExport: (v: boolean) => void;
  setErrorMessage: (msg: string | null) => void;
}

export const useUIStore = create<UISlice>((set) => ({
  selectedTab: "markers",
  showImport: false,
  showExport: false,
  errorMessage: null,

  setSelectedTab: (tab) => set({ selectedTab: tab }),
  setShowImport: (v) => set({ showImport: v }),
  setShowExport: (v) => set({ showExport: v }),
  setErrorMessage: (msg) => set({ errorMessage: msg }),
}));
