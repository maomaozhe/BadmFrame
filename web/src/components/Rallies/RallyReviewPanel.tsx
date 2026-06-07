import { Check, Clapperboard, Play, SkipForward, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import { useClipStore } from "@/store/clipSlice";
import { useRallyStore } from "@/store/rallySlice";
import { useVideoStore } from "@/store/videoSlice";
import { formatTimePrecise } from "@/utils";
import type { RallyCandidate, RallyReviewState } from "@/types";

interface Props {
  duration: number;
}

const STATE_LABELS: Record<RallyReviewState, string> = {
  pending: "待审",
  accepted: "确认",
  rejected: "删除",
  adjusted: "调整",
};

export function RallyReviewPanel({ duration }: Props) {
  const status = useRallyStore((s) => s.status);
  const candidates = useRallyStore((s) => s.candidates);
  const selectedCandidateId = useRallyStore((s) => s.selectedCandidateId);
  const selectCandidate = useRallyStore((s) => s.selectCandidate);
  const acceptCandidate = useRallyStore((s) => s.acceptCandidate);
  const rejectCandidate = useRallyStore((s) => s.rejectCandidate);
  const updateCandidate = useRallyStore((s) => s.updateCandidate);
  const createClipsFromRallyCandidates = useClipStore((s) => s.createClipsFromRallyCandidates);
  const seekTo = useVideoStore((s) => s.seekTo);
  const playRange = useVideoStore((s) => s.playRange);

  const selected = candidates.find((candidate) => candidate.id === selectedCandidateId) ?? candidates[0];
  const counts = countStates(candidates);
  const convertibleCount = candidates.filter(
    (candidate) => candidate.reviewState === "accepted" || candidate.reviewState === "adjusted"
  ).length;

  if (status === "idle") {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        尚未提取候选回合。
      </div>
    );
  }

  if (!selected) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        没有候选回合。
      </div>
    );
  }

  const selectedIndex = candidates.findIndex((candidate) => candidate.id === selected.id);

  return (
    <div className="p-3 space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill label="待审" value={counts.pending} />
        <StatusPill label="确认" value={counts.accepted} />
        <StatusPill label="删除" value={counts.rejected} />
        <StatusPill label="调整" value={counts.adjusted} />
        <button
          className="ml-auto inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-accent disabled:opacity-50"
          onClick={() => createClipsFromRallyCandidates(candidates)}
          disabled={convertibleCount === 0}
        >
          <Clapperboard className="h-3.5 w-3.5" />
          转换为片段
        </button>
      </div>

      <div className="grid gap-3 lg:grid-cols-[240px_1fr]">
        <div className="space-y-1">
          {candidates.map((candidate, index) => (
            <button
              key={candidate.id}
              className={`flex w-full items-center justify-between rounded-md border px-2 py-1.5 text-left transition-colors ${
                candidate.id === selected.id ? "border-primary bg-primary/10" : "hover:bg-accent"
              }`}
              onClick={() => selectCandidate(candidate.id)}
            >
              <span className="font-medium">#{index + 1}</span>
              <span className="font-mono text-xs">{formatTimePrecise(candidate.startSec)}</span>
              <span className={`rounded px-1.5 py-0.5 text-[11px] ${stateClass(candidate.reviewState)}`}>
                {STATE_LABELS[candidate.reviewState]}
              </span>
            </button>
          ))}
        </div>

        <div className="space-y-3 rounded-md border p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">候选回合 {selectedIndex + 1}</span>
            <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs">
              {formatTimePrecise(selected.startSec)} - {formatTimePrecise(selected.endSec)}
            </span>
            <span className="rounded bg-muted px-2 py-0.5 text-xs">
              {Math.round(selected.confidence * 100)}%
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <NumberField
              label="开始"
              value={selected.startSec}
              max={Math.max(0, selected.endSec - 0.1)}
              onChange={(value) => updateCandidate(selected.id, { startSec: value })}
            />
            <NumberField
              label="结束"
              value={selected.endSec}
              min={selected.startSec + 0.1}
              max={duration}
              onChange={(value) => updateCandidate(selected.id, { endSec: value })}
            />
            <ReadonlyStat label="可见" value={formatRatio(selected.trajectoryStats?.visibleRatio)} />
            <ReadonlyStat label="最大丢点" value={formatSeconds(selected.trajectoryStats?.maxGapSec)} />
          </div>

          <div className="flex flex-wrap gap-2">
            <IconButton title="确认" onClick={() => acceptCandidate(selected.id)}>
              <Check className="h-4 w-4" />
            </IconButton>
            <IconButton title="删除" onClick={() => rejectCandidate(selected.id)}>
              <Trash2 className="h-4 w-4" />
            </IconButton>
            <IconButton title="跳转" onClick={() => seekTo(selected.startSec)}>
              <SkipForward className="h-4 w-4" />
            </IconButton>
            <IconButton title="播放回合" onClick={() => playRange(selected.startSec, selected.endSec)}>
              <Play className="h-4 w-4" />
            </IconButton>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusPill({ label, value }: { label: string; value: number }) {
  return (
    <span className="rounded-md border px-2 py-1 text-xs">
      {label} <strong>{value}</strong>
    </span>
  );
}

function NumberField({
  label,
  value,
  min = 0,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="space-y-1">
      <span className="block text-xs text-muted-foreground">{label}</span>
      <input
        className="h-8 w-full rounded-md border bg-background px-2 font-mono text-xs"
        type="number"
        min={min}
        max={max}
        step={0.1}
        value={value}
        onChange={(event) => {
          const next = Number(event.target.value);
          if (Number.isFinite(next)) onChange(roundTime(next));
        }}
      />
    </label>
  );
}

function ReadonlyStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <span className="block text-xs text-muted-foreground">{label}</span>
      <span className="block h-8 rounded-md border bg-muted/30 px-2 py-1.5 font-mono text-xs">{value}</span>
    </div>
  );
}

function IconButton({
  title,
  onClick,
  children,
}: {
  title: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      className="inline-flex h-8 w-8 items-center justify-center rounded-md border hover:bg-accent"
      title={title}
      aria-label={title}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function countStates(candidates: RallyCandidate[]): Record<RallyReviewState, number> {
  return candidates.reduce<Record<RallyReviewState, number>>(
    (acc, candidate) => {
      acc[candidate.reviewState] += 1;
      return acc;
    },
    { pending: 0, accepted: 0, rejected: 0, adjusted: 0 }
  );
}

function stateClass(state: RallyReviewState): string {
  if (state === "accepted" || state === "adjusted") return "bg-emerald-500/15 text-emerald-700";
  if (state === "rejected") return "bg-zinc-500/15 text-zinc-600";
  return "bg-amber-500/15 text-amber-700";
}

function formatRatio(value?: number): string {
  if (value === undefined) return "-";
  return `${Math.round(value * 100)}%`;
}

function formatSeconds(value?: number): string {
  if (value === undefined) return "-";
  return `${value.toFixed(2)}s`;
}

function roundTime(value: number): number {
  return Math.round(value * 10) / 10;
}
