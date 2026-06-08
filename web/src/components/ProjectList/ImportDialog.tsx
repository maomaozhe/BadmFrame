import { useState, useRef } from "react";
import { useProjectStore } from "@/store/projectSlice";
import { useUIStore } from "@/store/uiSlice";
import { useVideoStore } from "@/store/videoSlice";
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { SourceVideo } from "@/types";
import { api } from "@/services/api";
import { generateId, formatTimePrecise, formatFileSize } from "@/utils";
import { uploadVideoForRally } from "@/services/rallyApi";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ImportDialog({ open, onClose }: Props) {
  const { setCurrentProject, upsertProject } = useProjectStore();
  const { setShowImport } = useUIStore();
  const fileRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<"select" | "review">("select");
  const [file, setFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState<SourceVideo | null>(null);
  const [projectName, setProjectName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileSelect = async (f: File | undefined) => {
    if (!f) return;
    setFile(f);
    setLoading(true);
    setError("");

    try {
      const url = URL.createObjectURL(f);
      const meta = await extractMetadata(f, url);
      setMetadata(meta);
      setProjectName(f.name.replace(/\.[^.]+$/, ""));
      setStep("review");
    } catch (e: any) {
      setError(e.message || "无法读取视频信息");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!metadata || !projectName.trim() || !file) return;
    setLoading(true);
    setError("");
    try {
      const uploaded = await api.uploadVideo(file);
      const project = await api.createProject(projectName.trim(), uploaded.serverVideoId || uploaded.id);
      const withPlayback = {
        ...project,
        sourceVideo: project.sourceVideo
          ? { ...project.sourceVideo, objectURL: metadata.objectURL }
          : { ...uploaded, objectURL: metadata.objectURL },
      };
      await upsertProject(withPlayback);
      setCurrentProject(withPlayback.id);
      resetDialog();
    } catch (e: any) {
      setError(e.message || "后端不可用，无法创建项目");
    } finally {
      setLoading(false);
    }
  };

  const resetDialog = () => {
    setStep("select");
    setFile(null);
    setMetadata(null);
    setProjectName("");
    setError("");
    onClose();
  };

  return (
    <Dialog open={open} onClose={resetDialog}>
      <DialogHeader>
        <DialogTitle>{step === "select" ? "导入视频" : "视频信息"}</DialogTitle>
      </DialogHeader>

      {step === "select" && (
        <div className="px-6 py-6 flex flex-col items-center gap-4">
          <span className="text-5xl">🎬</span>
          <p className="text-sm text-muted-foreground">
            支持 MP4、MOV 等常见视频格式
          </p>
          <input
            ref={fileRef}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files?.[0])}
          />
          <Button onClick={() => fileRef.current?.click()} size="lg">
            选择视频文件
          </Button>
          {loading && <p className="text-sm text-muted-foreground">读取中...</p>}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
      )}

      {step === "review" && metadata && (
        <>
          <div className="px-6 py-4 space-y-3">
            <div>
              <label className="text-sm font-medium">项目名称</label>
              <Input
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                className="mt-1"
              />
            </div>
            <div className="text-sm space-y-1 text-muted-foreground">
              <div className="flex justify-between"><span>文件名</span><span className="truncate max-w-[200px]">{metadata.fileName}</span></div>
              <div className="flex justify-between"><span>时长</span><span>{formatTimePrecise(metadata.durationSec)}</span></div>
              <div className="flex justify-between"><span>分辨率</span><span>{metadata.width}×{metadata.height}</span></div>
              <div className="flex justify-between"><span>帧率</span><span>{metadata.frameRate.toFixed(1)} fps</span></div>
              <div className="flex justify-between"><span>编码</span><span>{metadata.codec}</span></div>
              <div className="flex justify-between"><span>文件大小</span><span>{formatFileSize(metadata.fileSize)}</span></div>
              {metadata.isVFR && (
                <div className="flex justify-between text-yellow-500">
                  <span>可变帧率</span><span>⚠ 是</span>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={resetDialog}>取消</Button>
            <Button onClick={handleCreate} disabled={!projectName.trim() || loading}>
              {loading ? "创建中..." : "创建项目"}
            </Button>
          </DialogFooter>
        </>
      )}
    </Dialog>
  );
}

async function extractMetadata(file: File, url: string): Promise<SourceVideo> {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    video.preload = "metadata";

    video.onloadedmetadata = () => {
      const source: SourceVideo = {
        id: generateId(),
        fileName: file.name,
        filePath: "",
        durationSec: video.duration,
        width: video.videoWidth,
        height: video.videoHeight,
        frameRate: 0,
        codec: "未知",
        isVFR: false,
        fileSize: file.size,
        importDate: new Date().toISOString(),
        objectURL: url,
      };
      // 不在此处 revokeObjectURL，因为 objectURL 被存储在 SourceVideo 中
      // 供 VideoPlayer 后续使用，revoke 由 VideoPlayer 负责
      resolve(source);
    };

    video.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("无法读取视频文件，格式可能不支持"));
    };

    video.src = url;
  });
}
