import { useEffect, useRef } from "react";
import { useVideoStore } from "@/store/videoSlice";
import { useProjectStore } from "@/store/projectSlice";
import { formatTimePrecise } from "@/utils";

export function VideoPlayer() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const projects = useProjectStore((s) => s.projects);
  const { currentTime, duration, isPlaying, isLoading, setCurrentTime, setDuration, setIsPlaying, setIsLoading } =
    useVideoStore();

  const project = projects.find((p) => p.id === currentProjectId);
  const objectURL = project?.sourceVideo?.objectURL;

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !objectURL) return;

    setIsLoading(true);
    video.src = objectURL;

    const onLoaded = () => {
      setDuration(video.duration);
      setIsLoading(false);
    };
    const onTime = () => setCurrentTime(video.currentTime);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);

    video.addEventListener("loadedmetadata", onLoaded);
    video.addEventListener("timeupdate", onTime);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    video.addEventListener("ended", () => setIsPlaying(false));

    return () => {
      video.removeEventListener("loadedmetadata", onLoaded);
      video.removeEventListener("timeupdate", onTime);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("ended", () => setIsPlaying(false));
    };
  }, [objectURL]);

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
    <div className="bg-black relative shrink-0" style={{ aspectRatio: "16 / 9" }}>
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
