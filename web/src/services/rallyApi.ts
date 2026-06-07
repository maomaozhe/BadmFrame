import type { RallyAnalysisResult, RallyCandidate } from "@/types";

export interface RallyApplyOptions {
  includePending?: boolean;
  replaceExistingRally?: boolean;
}

export async function importRallyCandidates(
  videoId: string,
  candidates: RallyCandidate[]
): Promise<RallyAnalysisResult> {
  const durationSec = Math.max(0, ...candidates.map((candidate) => candidate.endSec));
  return {
    taskId: `mock-rally-task-${videoId}`,
    videoId,
    status: "completed",
    progress: 1,
    durationSec,
    candidates: candidates.slice().sort((a, b) => a.startSec - b.startSec),
  };
}

export async function getRallyResult(videoId: string, taskId: string): Promise<RallyAnalysisResult> {
  const candidates = createMockRallyCandidates(120);
  return {
    taskId,
    videoId,
    status: "completed",
    progress: 1,
    durationSec: 120,
    candidates,
  };
}

export async function applyRallies(
  projectId: string,
  taskId: string,
  options: RallyApplyOptions = {}
): Promise<{ createdClipIds: string[]; clipsCreated: number }> {
  void projectId;
  void taskId;
  void options;
  return { createdClipIds: [], clipsCreated: 0 };
}

export function createMockRallyCandidates(durationSec: number): RallyCandidate[] {
  if (durationSec <= 0) return [];
  const seedRanges: Array<[number, number, number]> = [
    [Math.min(8, durationSec * 0.08), Math.min(19, durationSec * 0.2), 0.84],
    [Math.min(25, durationSec * 0.28), Math.min(38, durationSec * 0.42), 0.77],
    [Math.min(46, durationSec * 0.52), Math.min(59, durationSec * 0.66), 0.72],
    [Math.min(68, durationSec * 0.74), Math.min(82, durationSec * 0.9), 0.68],
  ];

  return seedRanges
    .map(([start, end, confidence], index) => ({
      id: `mock-rally-${String(index + 1).padStart(3, "0")}`,
      startSec: roundTime(Math.max(0, Math.min(start, durationSec - 1))),
      endSec: roundTime(Math.min(durationSec, Math.max(end, start + 4))),
      confidence,
      reviewState: "pending" as const,
      startReason: ["trajectory_active", "mock_seed"],
      endReason: ["trajectory_missing", "mock_seed"],
      source: "imported-json" as const,
      trajectoryStats: {
        visibleRatio: roundTime(0.62 + index * 0.06),
        maxGapSec: roundTime(0.28 + index * 0.08),
        directionChanges: 5 + index * 2,
        meanSpeedPxSec: 760 + index * 95,
      },
    }))
    .filter((candidate) => candidate.endSec > candidate.startSec);
}

function roundTime(value: number): number {
  return Math.round(value * 100) / 100;
}
