import { useEffect, useRef, useState } from "react";
import { useVideoStore } from "@/store/videoSlice";
import { useProjectStore } from "@/store/projectSlice";
import { formatTimePrecise } from "@/utils";
import type { SourceVideo } from "@/types";

function getVideoURL(sourceVideo: SourceVideo | null): string | null {
  if (!sourceVideo) return null;
  if (sourceVideo.objectURL) return sourceVideo.objectURL;
  if (sourceVideo.id) return `/api/v1/videos/${sourceVideo.id}/file`;
  return null;
}

export function VideoPlayer() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const projects = useProjectStore((s) => s.projects);
  const {
    currentTime,
    duration,
    isPlaying,
    isLoading,
    seekRequest,
    playRequest,
    setCurrentTime,
    setDuration,
    setIsPlaying,
    setIsLoading,
    clearPlaybackRequest,
  } =
    useVideoStore();

  const project = projects.find((p) => p.id === currentProjectId);
  const videoURL = getVideoURL(project?.sourceVideo ?? null);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    setHasError(false);

    if (!videoURL) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    video.src = videoURL;

    const onLoaded = () => {
      setDuration(video.duration);
      setIsLoading(false);
      setHasError(false);
    };
    const onError = () => {
      setIsLoading(false);
      setHasError(true);
    };
    const onError = () => setIsLoading(false);
    const onTime = () => {
      setCurrentTime(video.currentTime);
      if (playRequest?.endSec !== undefined && video.currentTime >= playRequest.endSec) {
        video.pause();
        clearPlaybackRequest();
      }
    };
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onEnded = () => setIsPlaying(false);

    video.addEventListener("loadedmetadata", onLoaded);
    video.addEventListener("error", onError);
    video.addEventListener("timeupdate", onTime);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    video.addEventListener("ended", onEnded);

    return () => {
      video.removeEventListener("loadedmetadata", onLoaded);
      video.removeEventListener("error", onError);
      video.removeEventListener("timeupdate", onTime);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("ended", onEnded);
    };
  }, [objectURL, playRequest?.endSec]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || seekRequest === null) return;
    video.currentTime = Math.max(0, Math.min(seekRequest.timeSec, duration || seekRequest.timeSec));
  }, [seekRequest?.id, duration]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !playRequest) return;
    video.currentTime = Math.max(0, Math.min(playRequest.startSec, duration || playRequest.startSec));
    void video.play();
  }, [playRequest?.id, duration]);

  const handleTogglePlay = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) video.play();
    else video.pause();
  };

  const handleProgressClick = (e: React.MouseEvent) => {
    const video = videoRef.current;
    if (!video || duration <= 0 || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const fraction = (e.clientX - rect.left) / rect.width;
    const target = fraction * duration;
    video.currentTime = target;
  };

  return (
    <div className="bg-black relative shrink-0" style={{ aspectRatio: "16 / 9", maxHeight: "60dvh" }}>
      <video
        ref={videoRef}
        className="w-full h-full object-contain"
        playsInline
        preload="auto"
        onClick={handleTogglePlay}
      />

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60">
          <p className="text-white/70 text-sm">加载中...</p>
        </div>
      )}

      {hasError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 gap-2">
          <p className="text-red-400 text-sm">视频无法播放</p>
          <p className="text-white/50 text-xs">
            {project?.sourceVideo?.filePath
              ? "视频文件可能已被删除，请重新导入"
              : "视频尚未上传到服务器，请重新导入"}
          </p>
        </div>
      )}

      {!isLoading && (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3">
          <div className="flex items-center gap-3">
            <button onClick={handleTogglePlay} className="text-white text-xl">
              {isPlaying ? "⏸" : "▶"}
            </button>
            <span className="text-white text-xs font-mono">
              {formatTimePrecise(currentTime)}
            </span>
            <div
              ref={containerRef}
              className="flex-1 h-1.5 bg-white/30 rounded cursor-pointer"
              onClick={handleProgressClick}
            >
              <div
                className="h-full bg-primary rounded transition-all"
                style={{ width: duration > 0 ? `${(currentTime / duration) * 100}%` : "0%" }}
              />
            </div>
            <span className="text-white/60 text-xs font-mono">
              {formatTimePrecise(duration)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
