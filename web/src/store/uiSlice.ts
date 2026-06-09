import { create } from "zustand";
import type { EditorTab, ExportSortMode } from "@/types";

interface UISlice {
  selectedTab: EditorTab;
  showImport: boolean;
  showExport: boolean;
  exportSortMode: ExportSortMode;
  errorMessage: string | null;

  setSelectedTab: (tab: EditorTab) => void;
  setShowImport: (v: boolean) => void;
  setShowExport: (v: boolean) => void;
  setExportSortMode: (mode: ExportSortMode) => void;
  setErrorMessage: (msg: string | null) => void;
}

export const useUIStore = create<UISlice>((set) => ({
  selectedTab: "markers",
  showImport: false,
  showExport: false,
  exportSortMode: "position",
  errorMessage: null,

  setSelectedTab: (tab) => set({ selectedTab: tab }),
  setShowImport: (v) => set({ showImport: v }),
  setShowExport: (v) => set({ showExport: v }),
  setExportSortMode: (mode) => set({ exportSortMode: mode }),
  setErrorMessage: (msg) => set({ errorMessage: msg }),
}));
