import { create } from "zustand";

interface VideoSlice {
  videoFile: File | null;
  videoURL: string | null;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  isLoading: boolean;

  setVideoFile: (file: File | null) => void;
  setVideoURL: (url: string | null) => void;
  setCurrentTime: (t: number) => void;
  setDuration: (d: number) => void;
  setIsPlaying: (p: boolean) => void;
  setIsLoading: (l: boolean) => void;
  reset: () => void;
}

export const useVideoStore = create<VideoSlice>((set) => ({
  videoFile: null,
  videoURL: null,
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  isLoading: false,

  setVideoFile: (file) => set({ videoFile: file }),
  setVideoURL: (url) => set({ videoURL: url }),
  setCurrentTime: (t) => set({ currentTime: t }),
  setDuration: (d) => set({ duration: d }),
  setIsPlaying: (p) => set({ isPlaying: p }),
  setIsLoading: (l) => set({ isLoading: l }),
  reset: () =>
    set({
      videoFile: null,
      videoURL: null,
      currentTime: 0,
      duration: 0,
      isPlaying: false,
      isLoading: false,
    }),
}));
