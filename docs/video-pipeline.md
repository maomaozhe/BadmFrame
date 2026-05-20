# Video Pipeline

This document describes the intended media workflow for BadmFrame. It focuses on badminton editing needs and should become more precise as implementation decisions are made.

## Current Confirmed Content

- Video work is local-first.
- MVP video editing should focus on import, preview, manual clip selection, simple annotation, and export.
- Automatic badminton analysis is future scope unless explicitly requested.

## Intended Flow

1. Import or reference a source video.
2. Validate that the file can be read.
3. Load a preview for scrubbing and selection.
4. Let the user mark clip start and end times.
5. Attach simple annotations or labels to clips.
6. Queue export jobs for selected clips.
7. Report progress, completion, cancellation, or failure.
8. Preserve project metadata so clips can be revised later.

## Import

The import step should eventually capture:

- Original file path or media identifier.
- Duration, dimensions, frame rate, codec, and audio presence when available.
- Whether the file is readable by the chosen video engine.
- Any warning that may affect trimming or export.

## Timeline And Clip Selection

The timeline should eventually support:

- Scrubbing to inspect rallies and training moments.
- Start and end markers for a clip.
- Clip names or labels.
- A list of selected clips within the project.

The MVP can use manual selection only.

## Annotation

Annotations should start simple:

- Text note.
- Shot or rally label.
- Player or side label if needed.
- Coaching comment if needed.

Visual overlays, motion tracking, and shuttle trajectory are future scope.

## Export

Export should eventually support:

- Exporting a single selected clip.
- Exporting multiple selected clips.
- Keeping audio when available unless the user chooses otherwise.
- A small set of shareable presets once target platforms are known.

Exact formats and codecs are undecided.

## Failure Recovery

The pipeline should eventually handle:

- Unsupported media.
- Missing source video.
- Export cancellation.
- Export overwrite conflicts.
- Failed encoder process.
- Insufficient disk space if detectable.

Failures should be visible to the user and recoverable where practical.

## Open Questions

- Should trimming prioritize speed with stream copy or frame accuracy with re-encoding?
- Which export presets should exist first?
- Should the app generate proxy or thumbnail files for smoother previews?
- Should clips support multiple annotations or a single primary note in MVP?

## Agent Notes

- Use a proven media engine or library for core video operations once implementation starts.
- Keep large sample videos outside git unless a lightweight fixture policy is created.
- Prefer explicit job states over hidden background work.

## Update Triggers

Update this file when:

- A video engine is selected.
- Import metadata shape is defined.
- Export presets are chosen.
- Timeline or annotation behavior changes.
- Failure modes are implemented or revised.
