import { create } from "zustand";
import type { RallyCandidate } from "@/types";

type RallyStatus = "idle" | "running" | "completed" | "failed";

interface RallySlice {
  status: RallyStatus;
  candidates: RallyCandidate[];
  selectedCandidateId: string | null;
  taskId: string | null;
  error?: string;
  setStatus: (status: RallyStatus, error?: string) => void;
  setCandidates: (candidates: RallyCandidate[], taskId?: string | null) => void;
  updateCandidate: (id: string, updates: Partial<RallyCandidate>) => void;
  acceptCandidate: (id: string) => void;
  rejectCandidate: (id: string) => void;
  selectCandidate: (id: string | null) => void;
  resetRallies: () => void;
}

export const useRallyStore = create<RallySlice>((set, get) => ({
  status: "idle",
  candidates: [],
  selectedCandidateId: null,
  taskId: null,
  error: undefined,

  setStatus: (status, error) => set({ status, error }),

  setCandidates: (candidates, taskId = null) =>
    set({
      status: "completed",
      candidates: candidates.slice().sort((a, b) => a.startSec - b.startSec),
      selectedCandidateId: candidates[0]?.id ?? null,
      taskId,
      error: undefined,
    }),

  updateCandidate: (id, updates) =>
    set((state) => ({
      candidates: state.candidates.map((candidate) =>
        candidate.id === id
          ? {
              ...candidate,
              ...updates,
              reviewState:
                updates.reviewState ??
                (updates.startSec !== undefined || updates.endSec !== undefined ? "adjusted" : candidate.reviewState),
            }
          : candidate
      ),
    })),

  acceptCandidate: (id) => get().updateCandidate(id, { reviewState: "accepted" }),
  rejectCandidate: (id) => get().updateCandidate(id, { reviewState: "rejected" }),
  selectCandidate: (id) => set({ selectedCandidateId: id }),
  resetRallies: () =>
    set({
      status: "idle",
      candidates: [],
      selectedCandidateId: null,
      taskId: null,
      error: undefined,
    }),
}));
