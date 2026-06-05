# Rally Candidate Roadmap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build BadmFrame route A: automatically extract valid badminton rally candidates, let users quickly review and adjust them in the Web workbench, then convert confirmed rallies into clips for export.

**Architecture:** Web is the first user-facing validation surface. The model/algorithm layer is isolated behind JSON files and API contracts so TrackNetV3, another model, or offline inference can be swapped without changing the review workflow. iOS/Android remain the main product direction, but mobile model runtime is deliberately deferred until candidate quality and interaction patterns are proven on Web.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, FFmpeg/Celery baseline, React 19, TypeScript, Zustand, Playwright, pytest.

---

## Product Decisions

- Product route: prioritize an effective rally extraction engine, not a generic editor.
- First release surface: Web review workbench.
- First success bar: most real rallies are found; boundaries may be 1-3 seconds loose but must be quick to adjust.
- Review workflow: default to one-by-one quick review with keep/delete/boundary adjust.
- Output: confirmed rally candidates become normal clips and reuse the existing clip export and merged export flows.
- Mobile runtime: deferred. API and data shape should not assume cloud forever, but the first implementation may use server/offline JSON ingestion.

## Public Contract

Use a new rally-candidate contract instead of extending the paused `AutoClipSegment` keep/cut contract.

```ts
export type RallyReviewState = "pending" | "accepted" | "rejected" | "adjusted";

export interface RallyCandidate {
  id: string;
  startSec: number;
  endSec: number;
  confidence: number;
  reviewState: RallyReviewState;
  startReason: string[];
  endReason: string[];
  source: "model" | "imported-json" | "manual";
  trajectoryStats?: {
    visibleRatio?: number;
    maxGapSec?: number;
    directionChanges?: number;
    meanSpeedPxSec?: number;
  };
}
```

Backend response shape:

```json
{
  "task_id": "uuid",
  "video_id": "uuid",
  "project_id": "uuid",
  "status": "completed",
  "progress": 1,
  "duration_sec": 120,
  "candidates": [
    {
      "id": "rally-001",
      "start_sec": 14,
      "end_sec": 21,
      "confidence": 0.82,
      "review_state": "pending",
      "start_reason": ["trajectory_active"],
      "end_reason": ["trajectory_missing"],
      "source": "imported-json",
      "trajectory_stats": { "visible_ratio": 0.7, "max_gap_sec": 0.4 }
    }
  ],
  "error": null
}
```

Keep the existing old analysis code as a deprecated experiment until the rally path is stable. Do not delete it in the first pass.

## Parallel Workstreams

These streams can start in parallel after the contract above is accepted:

- Evaluation and JSON tooling: Tasks 1-3.
- Backend rally API and persistence: Tasks 4-6.
- Web review UI and state: Tasks 7-10.
- E2E, docs, and product cleanup: Tasks 11-13.

Hard dependency: Web UI should use mocked or imported rally JSON until backend endpoints are ready. Backend should not depend on TrackNetV3 being runnable locally.

## Task 1: Add Rally Candidate Types

**Files:**
- Modify: `web/src/types.ts`
- Create: `server/app/schemas/rally.py`
- Test: `server/tests/test_rally_schemas.py`

**Step 1: Write backend schema tests**

Create tests that validate:

- `RallyCandidateRead` accepts pending candidates.
- confidence must be between 0 and 1.
- `end_sec` must be greater than `start_sec`.

Run:

```bash
cd server
./.venv/bin/pytest tests/test_rally_schemas.py -v
```

Expected: fail because schema does not exist.

**Step 2: Implement schemas**

Create Pydantic models in `server/app/schemas/rally.py`:

- `RallyReviewState = Literal["pending", "accepted", "rejected", "adjusted"]`
- `RallySource = Literal["model", "imported-json", "manual"]`
- `TrajectoryStats`
- `RallyCandidateRead`
- `RallyAnalysisResultRead`
- `RallyCandidateUpdate`
- `RallyCandidatesApplyRequest`
- `RallyCandidatesApplyResponse`

Add a model validator so `end_sec > start_sec`.

**Step 3: Add frontend types**

Add `RallyCandidate`, `RallyReviewState`, `RallyAnalysisResult`, and `TrajectoryStats` to `web/src/types.ts`. Keep old `AutoClipDraft` types for compatibility during migration.

**Step 4: Verify**

Run:

```bash
cd server
./.venv/bin/pytest tests/test_rally_schemas.py -v
cd ../web
npm run build
```

Commit:

```bash
git add web/src/types.ts server/app/schemas/rally.py server/tests/test_rally_schemas.py
git commit -m "feat: add rally candidate contract"
```

## Task 2: Add Evaluation Script for Manual Annotations

**Files:**
- Create: `server/app/services/rally_evaluation.py`
- Create: `server/tests/test_rally_evaluation.py`
- Read: `assets/reference/rally_annotations_140.json`

**Step 1: Write failing tests**

Test these metrics:

- exact overlap candidate has low boundary error.
- missing annotation increments `missed_rallies`.
- extra candidate increments `false_rallies`.
- merged candidate increments `merged_rallies` when one candidate overlaps multiple annotations.

Run:

```bash
cd server
./.venv/bin/pytest tests/test_rally_evaluation.py -v
```

Expected: fail because service does not exist.

**Step 2: Implement minimal evaluator**

Implement pure functions:

- `load_annotations(path: Path) -> list[RallyInterval]`
- `evaluate_candidates(annotations, candidates, overlap_threshold=0.3) -> RallyEvaluation`

Metrics required:

- `matched_rallies`
- `missed_rallies`
- `false_rallies`
- `merged_rallies`
- `mean_start_error_sec`
- `mean_end_error_sec`

No model inference in this task.

**Step 3: Verify with reference file**

Add a test that loads `assets/reference/rally_annotations_140.json` and confirms it contains 8 rallies.

Run:

```bash
cd server
./.venv/bin/pytest tests/test_rally_evaluation.py -v
```

Commit:

```bash
git add server/app/services/rally_evaluation.py server/tests/test_rally_evaluation.py
git commit -m "feat: evaluate rally candidates against annotations"
```

## Task 3: Add Imported JSON Rally Source

**Files:**
- Create: `server/app/services/rally_import.py`
- Create: `server/tests/test_rally_import.py`

**Step 1: Write failing import tests**

Test that a JSON file with `candidates` is parsed into `RallyCandidateRead` objects, sorted by `start_sec`, and rejects invalid ranges.

**Step 2: Implement importer**

Support this file shape:

```json
{
  "video": "sample.mp4",
  "source": "imported-json",
  "candidates": [
    {
      "id": "rally-001",
      "startSec": 14,
      "endSec": 21,
      "confidence": 0.8,
      "startReason": ["manual_seed"],
      "endReason": ["manual_seed"]
    }
  ]
}
```

Normalize camelCase input to snake_case schema fields. Default `review_state` to `pending` and `source` to `imported-json`.

**Step 3: Verify**

Run:

```bash
cd server
./.venv/bin/pytest tests/test_rally_import.py -v
```

Commit:

```bash
git add server/app/services/rally_import.py server/tests/test_rally_import.py
git commit -m "feat: import rally candidates from json"
```

## Task 4: Add Backend Rally API

**Files:**
- Create: `server/app/api/rallies.py`
- Modify: `server/app/main.py`
- Create: `server/tests/test_rally_api.py`

**Step 1: Write API tests**

Cover:

- `POST /api/v1/videos/{video_id}/rallies/import` accepts candidate JSON body and returns completed result.
- `GET /api/v1/videos/{video_id}/rallies/{task_id}` returns the stored result.
- missing video returns 404.
- invalid candidate range returns 422.

Use the same SQLite override style as `server/tests/test_analysis.py`.

**Step 2: Implement routes**

Add routes:

- `POST /api/v1/videos/{video_id}/rallies/import`
- `GET /api/v1/videos/{video_id}/rallies/{task_id}`

For V1, store results as JSON files under `settings.storage_dir / "rallies"`, matching the old analysis result pattern. Do not add a DB migration yet.

**Step 3: Register router**

Add the router to `server/app/main.py` with the existing API prefix style.

**Step 4: Verify**

Run:

```bash
cd server
./.venv/bin/pytest tests/test_rally_api.py -v
./.venv/bin/pytest tests/test_analysis.py -v
```

Commit:

```bash
git add server/app/api/rallies.py server/app/main.py server/tests/test_rally_api.py
git commit -m "feat: add rally candidate api"
```

## Task 5: Apply Confirmed Rallies to Clips

**Files:**
- Modify: `server/app/api/rallies.py`
- Test: `server/tests/test_rally_api.py`
- Modify: `web/src/store/clipSlice.ts`

**Step 1: Write apply tests**

Backend test:

- applying accepted/adjusted candidates creates clips.
- rejected and pending candidates are ignored by default.
- clip labels are `有效回合 1`, `有效回合 2`.
- clip notes include `source:rally-candidate` and candidate confidence.

Frontend store test can be added only if a test harness already exists. If not, cover this through Playwright in Task 11.

**Step 2: Implement backend apply route**

Add:

- `POST /api/v1/projects/{project_id}/rallies/apply`

Default behavior:

- body includes `task_id`.
- create clips from candidates whose `review_state` is `accepted` or `adjusted`.
- optional `include_pending=false`.
- optional `replace_existing_rally=false`.

**Step 3: Implement frontend clip helper**

Add `createClipsFromRallyCandidates(candidates)` to `web/src/store/clipSlice.ts`. It should mirror `createClipsFromAutoSegments` but use accepted/adjusted rally candidates and `source:rally-candidate`.

**Step 4: Verify**

Run:

```bash
cd server
./.venv/bin/pytest tests/test_rally_api.py -v
cd ../web
npm run build
```

Commit:

```bash
git add server/app/api/rallies.py server/tests/test_rally_api.py web/src/store/clipSlice.ts
git commit -m "feat: apply confirmed rallies to clips"
```

## Task 6: Add Model Runner Placeholder

**Files:**
- Create: `server/app/services/rally_runner.py`
- Create: `server/tests/test_rally_runner.py`
- Modify: `docs/rally-segmentation.md`

**Step 1: Write failing tests**

Test that the runner can:

- return imported JSON candidates when `BADMFRAME_RALLY_CANDIDATES_PATH` is set.
- fail explicitly when no runner source is configured.

**Step 2: Implement placeholder runner**

Do not integrate TrackNetV3 yet. Implement a boundary layer:

- `run_rally_detection(video_path: Path, duration_sec: float) -> list[RallyCandidateRead]`
- if env var JSON path exists, import it.
- otherwise raise `RuntimeError("Rally detection runner is not configured")`.

**Step 3: Document the boundary**

Update `docs/rally-segmentation.md` to state that V1 uses imported JSON or a configured external runner, and that TrackNetV3 integration is a later task.

**Step 4: Verify**

Run:

```bash
cd server
./.venv/bin/pytest tests/test_rally_runner.py -v
```

Commit:

```bash
git add server/app/services/rally_runner.py server/tests/test_rally_runner.py docs/rally-segmentation.md
git commit -m "feat: add rally detection runner boundary"
```

## Task 7: Replace Web Auto Tab with Rally Review State

**Files:**
- Modify: `web/src/types.ts`
- Modify: `web/src/components/Editor/EditorView.tsx`
- Create: `web/src/components/Rallies/RallyReviewPanel.tsx`
- Create: `web/src/store/rallySlice.ts`

**Step 1: Add rally store**

Implement Zustand state:

- current draft/result status.
- candidates.
- selected candidate id.
- actions: `setCandidates`, `updateCandidate`, `acceptCandidate`, `rejectCandidate`, `selectCandidate`, `resetRallies`.

**Step 2: Wire Editor tab**

Change the tab label from `自动` to `回合`. Keep the header button text as `提取回合`.

In the first frontend-only pass, `提取回合` may load deterministic local mock candidates from video duration. The shape must be `RallyCandidate`, not old `AutoClipSegment`.

**Step 3: Add panel**

`RallyReviewPanel` should show:

- status summary.
- candidate count by pending/accepted/rejected/adjusted.
- selected candidate time range and confidence.
- buttons: accept, reject, jump/play candidate.
- numeric inputs for start/end seconds.
- button: convert accepted to clips.

**Step 4: Verify**

Run:

```bash
cd web
npm run build
```

Commit:

```bash
git add web/src/types.ts web/src/components/Editor/EditorView.tsx web/src/components/Rallies/RallyReviewPanel.tsx web/src/store/rallySlice.ts
git commit -m "feat: add rally review workspace"
```

## Task 8: Show Rally Boundaries on Timeline

**Files:**
- Modify: `web/src/components/Timeline/TimelineView.tsx`
- Modify: `web/src/components/Editor/EditorView.tsx`
- Test: existing Playwright tests after Task 11

**Step 1: Inspect existing timeline props**

Read `TimelineView.tsx` and keep marker/clip behavior unchanged.

**Step 2: Add rally overlay prop**

Add optional prop:

```ts
rallyCandidates?: RallyCandidate[];
selectedRallyId?: string | null;
onSelectRally?: (id: string) => void;
```

Render accepted/adjusted candidates with a keep color, rejected with muted styling, pending with neutral styling, and selected candidate with stronger outline.

**Step 3: Wire EditorView**

Pass rally candidates from `rallySlice` to timeline.

**Step 4: Verify**

Run:

```bash
cd web
npm run build
```

Commit:

```bash
git add web/src/components/Timeline/TimelineView.tsx web/src/components/Editor/EditorView.tsx
git commit -m "feat: show rally candidates on timeline"
```

## Task 9: Add Quick Review Playback Behavior

**Files:**
- Modify: `web/src/store/videoSlice.ts`
- Modify: `web/src/components/Rallies/RallyReviewPanel.tsx`
- Modify: `web/src/components/Editor/VideoPlayer.tsx`

**Step 1: Add video actions if missing**

Add or reuse actions to seek to a candidate start time. Do not create a second video playback state system.

**Step 2: Implement jump and preview**

In `RallyReviewPanel`:

- `跳转` seeks to `startSec`.
- `播放回合` seeks to `startSec` and plays.
- when playback reaches `endSec`, pause or stop preview mode.

**Step 3: Verify manually and with build**

Run:

```bash
cd web
npm run build
```

Commit:

```bash
git add web/src/store/videoSlice.ts web/src/components/Rallies/RallyReviewPanel.tsx web/src/components/Editor/VideoPlayer.tsx
git commit -m "feat: add rally quick review playback"
```

## Task 10: Connect Web to Rally API

**Files:**
- Create or modify: `web/src/services/rallyApi.ts`
- Modify: `web/src/components/Rallies/RallyReviewPanel.tsx`
- Modify: `web/src/components/Editor/EditorView.tsx`

**Step 1: Add service client**

Implement functions:

- `importRallyCandidates(videoId, candidates)`
- `getRallyResult(videoId, taskId)`
- `applyRallies(projectId, taskId, options)`

If the current Web app still runs mostly local/IndexedDB, keep a local mock fallback behind a single function. Do not scatter mock creation across components.

**Step 2: Wire extraction action**

`提取回合` should:

- use backend if `project.sourceVideo.id` is available and API base is configured.
- otherwise use deterministic local candidates for frontend-only E2E.
- always populate `rallySlice`.

**Step 3: Wire apply action**

`转换为片段` should:

- call backend apply route when a backend task exists.
- otherwise use `createClipsFromRallyCandidates`.

**Step 4: Verify**

Run:

```bash
cd web
npm run build
cd ../server
./.venv/bin/pytest tests/test_rally_api.py -v
```

Commit:

```bash
git add web/src/services/rallyApi.ts web/src/components/Rallies/RallyReviewPanel.tsx web/src/components/Editor/EditorView.tsx
git commit -m "feat: connect rally review to api"
```

## Task 11: Add Web E2E for Rally Review

**Files:**
- Create: `web/e2e/tests/11-rally-review.spec.ts`
- Modify: `web/e2e/helpers/index.ts` only if helper exports are needed

**Step 1: Write E2E scenarios**

Cover:

- clicking `提取回合` opens the `回合` tab and shows candidates.
- accepting and rejecting candidates updates counts.
- editing start/end marks candidate as adjusted.
- converting accepted/adjusted candidates creates clips.
- export button becomes enabled after conversion.

**Step 2: Run targeted E2E**

Run:

```bash
cd web
npm run test:e2e -- 11-rally-review.spec.ts
```

If the repo's Playwright command does not support file filtering, run the full suite:

```bash
npm run test:e2e
```

**Step 3: Commit**

```bash
git add web/e2e/tests/11-rally-review.spec.ts web/e2e/helpers/index.ts
git commit -m "test: cover rally review workflow"
```

## Task 12: Product Copy and Deprecated Auto Path Cleanup

**Files:**
- Modify: `web/src/components/Editor/EditorView.tsx`
- Modify: `web/src/components/Rallies/RallyReviewPanel.tsx`
- Modify: `docs/product.md`
- Modify: `docs/video-pipeline.md`

**Step 1: Update naming**

Use these product terms:

- `提取回合`
- `候选回合`
- `逐个快审`
- `确认片段`
- `导出合辑`

Avoid promising:

- `自动精彩球`
- `一键最终成片`
- `AI 精彩程度判断`

**Step 2: Update docs**

Document that the first user-facing route is rally candidates and quick review. Keep old dead-time analysis documented as paused.

**Step 3: Verify**

Run:

```bash
cd web
npm run build
```

Commit:

```bash
git add web/src/components/Editor/EditorView.tsx web/src/components/Rallies/RallyReviewPanel.tsx docs/product.md docs/video-pipeline.md
git commit -m "docs: align product copy around rally extraction"
```

## Task 13: Final Verification

**Files:**
- No new files expected.

**Step 1: Run backend tests**

```bash
cd server
./.venv/bin/pytest
```

Expected: all tests pass.

**Step 2: Run Web build and E2E**

```bash
cd web
npm run build
npm run test:e2e
```

Expected: build passes and Playwright suite passes.

**Step 3: Review git diff**

```bash
git status --short
git diff --stat
```

Expected: only rally roadmap implementation files and docs changed.

**Step 4: Commit final fixes if any**

Use a focused commit message, for example:

```bash
git add <changed-files>
git commit -m "chore: finalize rally candidate workflow"
```

## Acceptance Criteria

- Web user can trigger rally extraction and see candidate rallies.
- User can review candidates one by one, accept, reject, and adjust boundaries.
- Accepted/adjusted candidates convert into normal clips.
- Existing export and merged export flows work with these clips.
- Backend has a rally candidate API and imported JSON path independent of TrackNetV3.
- Evaluation tooling can compare candidates against `assets/reference/rally_annotations_140.json`.
- Old auto-dead-time route is not presented as the primary product path.

## Defaults and Assumptions

- Keep old analysis code during V1 migration.
- Store V1 rally results as JSON files, not DB tables.
- Do not implement TrackNetV3 integration in this plan.
- Do not implement mobile runtime in this plan.
- Do not upload or commit large videos, model weights, inference caches, or generated exports.
- If Web backend integration is blocked, complete the review workflow against deterministic local rally candidates and keep the API service boundary intact.
