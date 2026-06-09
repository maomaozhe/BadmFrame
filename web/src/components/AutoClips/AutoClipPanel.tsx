import { Check, RotateCcw, Scissors, Trash2 } from "lucide-react";
import { formatTimePrecise } from "@/utils";
import type { AutoClipDraft, AutoClipMode, AutoClipSegment } from "@/types";

interface Props {
  draft: AutoClipDraft | null;
  duration: number;
  onRun: (mode: AutoClipMode) => void;
  onUpdateSegment: (segmentId: string, updates: Partial<AutoClipSegment>) => void;
  onApply: () => void;
}

export function AutoClipPanel({ draft, duration, onRun, onUpdateSegment, onApply }: Props) {
  const mode = draft?.mode ?? "balanced";
  const keepSegments = draft?.segments.filter((segment) => segment.state === "keep") ?? [];
  const cutSegments = draft?.segments.filter((segment) => segment.state === "cut") ?? [];
  const keepSec = keepSegments.reduce((sum, segment) => sum + segment.endSec - segment.startSec, 0);
  const cutSec = Math.max(0, duration - keepSec);

  // Simulate progress during the long tracknet stage
  const simulatedProgress = useSimulatedProgress(draft);

  const displayProgress =
    draft?.status === "running" && draft.stage === "tracknet"
      ? simulatedProgress
      : draft?.progress ?? 0;

  const handleApply = () => {
    // Remove previous auto clips first (reversible)
    removeAutoClips();
    const ids = createClipsFromAutoSegments(keepSegments);
    setAppliedClipIds(ids);
    setApplied(true);
  };

  const handleUndo = () => {
    for (const id of appliedClipIds) {
      deleteClip(id);
    }
    setAppliedClipIds([]);
    setApplied(false);
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="sticky top-0 z-10 border-b bg-background px-3 py-2">
        <div className="flex items-center gap-2">
          <select
            value={mode}
            onChange={(event) => onRun(event.target.value as AutoClipMode)}
            className="h-8 rounded-md border bg-background px-2 text-sm"
            disabled={draft?.status === "running"}
          >
            <option value="conservative">保守</option>
            <option value="balanced">平衡</option>
            <option value="aggressive">激进</option>
          </select>
          <button
            onClick={() => {
              setApplied(false);
              setAppliedClipIds([]);
              onRun(mode);
            }}
            className="inline-flex h-8 items-center gap-1 rounded-md border px-2 text-sm hover:bg-accent disabled:opacity-50"
            disabled={draft?.status === "running" || duration <= 0}
          >
            <Scissors className="h-4 w-4" />
            自动剪辑
          </button>
          <button
            onClick={onApply}
            className="ml-auto inline-flex h-8 items-center gap-1 rounded-md bg-primary px-2 text-sm text-primary-foreground disabled:opacity-50"
            disabled={keepSegments.length === 0 || !draft?.taskId}
          >
            <Check className="h-4 w-4" />
            应用
          </button>
        </div>
        {draft?.status === "running" && (
          <div className="mt-2 space-y-1">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{draft.message || draft.stage || "Running"}</span>
              <span>{Math.round(displayProgress * 100)}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-primary transition-all" style={{ width: `${displayProgress * 100}%` }} />
            </div>
            <button
              onClick={onCancel}
              className="mt-1 inline-flex h-7 items-center gap-1 rounded-md border border-destructive/30 px-2 text-xs text-destructive hover:bg-destructive/10"
            >
              取消分析
            </button>
          </div>
        )}
        {draft?.status === "failed" && (
          <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/10 px-2 py-1 text-xs text-destructive">
            {draft.error || draft.message || "Rally detection failed"}
          </div>
        )}
        {draft?.status === "completed" && (
          <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
            <Metric label="候选" value={`${keepSegments.length}`} />
            <Metric label="保留" value={formatTimePrecise(keepSec)} />
            <Metric label="剪掉" value={formatTimePrecise(cutSec)} />
          </div>
        )}
      </div>

      {!draft && (
        <div className="flex h-48 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
          <Scissors className="h-8 w-8" />
          <p className="text-sm">还没有自动剪辑草稿</p>
        </div>
      )}

      {draft?.status === "completed" && (
        <div className="divide-y">
          {draft.segments.map((segment) => (
            <SegmentRow key={segment.id} segment={segment} onUpdateSegment={onUpdateSegment} />
          ))}
        </div>
      )}
    </div>
  );
}

function SegmentRow({
  segment,
  onUpdateSegment,
}: {
  segment: AutoClipSegment;
  onUpdateSegment: (segmentId: string, updates: Partial<AutoClipSegment>) => void;
}) {
  const isKeep = segment.state === "keep";
  const seekTo = (t: number) => {
    const video = document.querySelector("video");
    if (video) video.currentTime = t;
  };

  return (
    <div className="px-3 py-2 hover:bg-accent/50">
      <div className="flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${isKeep ? "bg-emerald-500" : "bg-zinc-400"}`} />
        <span className="flex-1 text-sm font-medium">{isKeep ? "保留区间" : "剪掉区间"}</span>
        <span className="text-xs text-muted-foreground">{Math.round(segment.confidence * 100)}%</span>
        <button
          onClick={() => onUpdateSegment(segment.id, { state: isKeep ? "cut" : "keep" })}
          className="inline-flex h-7 w-7 items-center justify-center rounded-md border hover:bg-background"
          title={isKeep ? "删除候选" : "恢复候选"}
        >
          {isKeep ? <Trash2 className="h-3.5 w-3.5" /> : <RotateCcw className="h-3.5 w-3.5" />}
        </button>
      </div>
      <div className="mt-1 flex items-center gap-2">
        <button onClick={() => seekTo(segment.startSec)} className="font-mono text-xs text-blue-500 hover:underline">
          {formatTimePrecise(segment.startSec)}
        </button>
        <span className="text-xs text-muted-foreground">→</span>
        <button onClick={() => seekTo(segment.endSec)} className="font-mono text-xs text-blue-500 hover:underline">
          {formatTimePrecise(segment.endSec)}
        </button>
        <span className="text-xs text-muted-foreground">
          ({formatTimePrecise(segment.endSec - segment.startSec)})
        </span>
      </div>
      <p className="mt-1 truncate text-xs text-muted-foreground">{segment.reason.join(" / ")}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border px-2 py-1">
      <div className="text-muted-foreground">{label}</div>
      <div className="font-mono">{value}</div>
    </div>
  );
}

/**
 * Simulate progress during the long-running tracknet stage.
 * TrackNetV3 takes ~0.7s per frame, so ~7 min for a 10-min 30fps video.
 * We interpolate from 0.03 to 0.65 over a conservative estimate.
 */
function useSimulatedProgress(draft: AutoClipDraft | null): number {
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startRef = useRef<number>(0);

  useEffect(() => {
    if (draft?.status === "running" && draft.stage === "tracknet") {
      if (!startRef.current) {
        startRef.current = Date.now();
      }
      // Estimate ~10 min for a full video; cap at 0.65 so it doesn't look stuck
      const estimatedMs = 10 * 60 * 1000;
      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - startRef.current;
        const simulated = 0.03 + (0.65 - 0.03) * Math.min(1, elapsed / estimatedMs);
        setProgress(Math.round(simulated * 100) / 100);
      }, 1000);
    } else {
      startRef.current = 0;
      setProgress(0);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [draft?.status, draft?.stage]);

  return progress;
}
