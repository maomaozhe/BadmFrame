import { create } from "zustand";

interface VideoSlice {
  videoFile: File | null;
  videoURL: string | null;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  isLoading: boolean;
  seekRequest: { timeSec: number; id: number } | null;
  playRequest: { startSec: number; endSec?: number; id: number } | null;

  setVideoFile: (file: File | null) => void;
  setVideoURL: (url: string | null) => void;
  setCurrentTime: (t: number) => void;
  setDuration: (d: number) => void;
  setIsPlaying: (p: boolean) => void;
  setIsLoading: (l: boolean) => void;
  seekTo: (t: number) => void;
  playRange: (startSec: number, endSec: number) => void;
  clearPlaybackRequest: () => void;
  reset: () => void;
}

export const useVideoStore = create<VideoSlice>((set) => ({
  videoFile: null,
  videoURL: null,
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  isLoading: false,
  seekRequest: null,
  playRequest: null,

  setVideoFile: (file) => set({ videoFile: file }),
  setVideoURL: (url) => set({ videoURL: url }),
  setCurrentTime: (t) => set({ currentTime: t }),
  setDuration: (d) => set({ duration: d }),
  setIsPlaying: (p) => set({ isPlaying: p }),
  setIsLoading: (l) => set({ isLoading: l }),
  seekTo: (t) =>
    set((state) => ({
      seekRequest: { timeSec: Math.max(0, t), id: (state.seekRequest?.id ?? 0) + 1 },
    })),
  playRange: (startSec, endSec) =>
    set((state) => ({
      playRequest: {
        startSec: Math.max(0, startSec),
        endSec: Math.max(startSec, endSec),
        id: (state.playRequest?.id ?? 0) + 1,
      },
      seekRequest: null,
    })),
  clearPlaybackRequest: () => set({ seekRequest: null, playRequest: null }),
  reset: () =>
    set({
      videoFile: null,
      videoURL: null,
      currentTime: 0,
      duration: 0,
      isPlaying: false,
      isLoading: false,
      seekRequest: null,
      playRequest: null,
    }),
}));
