import { useEffect, useCallback, useRef } from "react";
import { useVideoStore } from "@/store/videoSlice";

export function useVideoPlayer() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const {
    videoURL,
    currentTime,
    duration,
    isPlaying,
    isLoading,
    setCurrentTime,
    setDuration,
    setIsPlaying,
    setIsLoading,
  } = useVideoStore();

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onLoaded = () => {
      setDuration(video.duration);
      setIsLoading(false);
    };
    const onTime = () => setCurrentTime(video.currentTime);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onEnded = () => setIsPlaying(false);

    video.addEventListener("loadedmetadata", onLoaded);
    video.addEventListener("timeupdate", onTime);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    video.addEventListener("ended", onEnded);

    return () => {
      video.removeEventListener("loadedmetadata", onLoaded);
      video.removeEventListener("timeupdate", onTime);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("ended", onEnded);
    };
  }, [videoURL]);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) video.play();
    else video.pause();
  }, []);

  const seekTo = useCallback((seconds: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = seconds;
  }, []);

  const loadVideo = useCallback((url: string) => {
    setIsLoading(true);
    // Release old URL
    const prev = useVideoStore.getState().videoURL;
    if (prev && prev.startsWith("blob:")) {
      URL.revokeObjectURL(prev);
    }
    useVideoStore.getState().setVideoURL(url);
  }, []);

  return { videoRef, togglePlay, seekTo, loadVideo };
}
