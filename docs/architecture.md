# Architecture Notes

This document records the intended architecture direction for BadmFrame. It should describe real decisions once they exist and clearly label placeholders while the stack is undecided.

## Current Confirmed Content

- No frontend framework has been selected.
- No backend/runtime model has been selected.
- No video processing engine has been selected.
- The application should be designed around local video workflows first.

## Target Architecture Shape

BadmFrame will likely need these subsystems:

- User interface: project browser, video preview, timeline, clip list, annotation controls, export status.
- Project model: source media references, clip ranges, annotations, export settings, and project metadata.
- Video pipeline: import validation, preview generation if needed, trimming, encoding, and export.
- Storage: local project files plus references to source media and generated exports.
- Job execution: long-running video tasks with progress, cancellation, retry, and failure messages.

## Frontend Placeholder

The frontend should eventually provide:

- Fast timeline navigation.
- Clear clip boundary editing.
- Annotation controls that do not obscure the video.
- Export progress and failure recovery.

Technology decision is pending. Do not choose a framework without recording an ADR.

## Backend And Runtime Placeholder

The runtime should eventually provide:

- Access to local files.
- Durable project persistence.
- Background video processing jobs.
- A clean boundary between UI state and media-processing state.

Technology decision is pending. Options may include a web app, desktop app, or local-first hybrid.

## Video Processing Placeholder

The video engine should eventually support:

- Reading common phone and camera video formats.
- Accurate or near-accurate trimming.
- Exporting common shareable formats.
- Clear error messages when codecs or files are unsupported.

FFmpeg is a likely candidate, but this is not yet a decision.

## Storage Placeholder

The storage model should eventually distinguish:

- Source videos, which may be large and should not be copied unless necessary.
- Project metadata, which should be small and durable.
- Generated previews or caches, which can be recreated.
- Exported clips, which are user-facing artifacts.

## Open Questions

- Should the product be a desktop app for reliable local file access?
- Should video processing run in-process, in a worker process, or in a separate service?
- What project file format should be used?
- How should missing source media be handled when a project is reopened?

## Agent Notes

- Do not present placeholder architecture as implemented behavior.
- When adding code, keep media processing behind an explicit boundary so UI code does not directly shell out everywhere.
- Record major stack, storage, and pipeline decisions in `docs/decisions/`.

## Update Triggers

Update this file when:

- A technology stack is selected.
- Repository structure changes.
- Project file format is chosen.
- Video processing strategy changes.
- Background job behavior is implemented.
