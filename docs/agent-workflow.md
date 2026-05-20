# Agent Workflow

This document defines how coding agents should work in BadmFrame.

## Current Confirmed Content

- This repository begins with documentation, not app code.
- `AGENTS.md` is the entry point for all agent work.
- Architecture and product decisions should be recorded before they become hard to reverse.

## Before Starting Work

For any non-trivial task:

- Read `AGENTS.md`.
- Read the most relevant product, architecture, or video pipeline document.
- Check existing decision records under `docs/decisions/`.
- Inspect the current repository before assuming structure or stack.

## During Work

- Keep changes scoped to the user request.
- Prefer established project patterns once they exist.
- Add or update tests when behavior changes.
- Update docs when commands, architecture, product behavior, or workflow changes.
- Preserve user changes and unrelated files.

## Decision Records

Create a new ADR in `docs/decisions/` when a change selects or materially changes:

- App platform or framework.
- Video processing engine.
- Project file format.
- Storage layout.
- Export strategy.
- Task/job execution model.

Use a filename like:

```text
0002-short-decision-title.md
```

## Testing Expectations

Until code exists, documentation changes should be checked by reading links and confirming the agent entry flow works.

Once code exists:

- Add targeted tests for changed behavior.
- Run the relevant test command before finalizing.
- If a command cannot run, report why and what remains unverified.

## Change Summary Expectations

When finishing a task, report:

- What changed.
- Which files matter most.
- What validation was run.
- Any remaining gaps or assumptions.

## Open Questions

- What commit and PR conventions should be used?
- Should task specs live in `tasks/`, issues, or another tracker?
- Should the project use ADRs for product decisions as well as technical decisions?

## Agent Notes

- Treat docs as the project memory, not decoration.
- Keep future agents oriented by updating links and commands as soon as they become real.
- Do not add speculative implementation detail that has not been requested or decided.

## Update Triggers

Update this file when:

- The development workflow changes.
- Test, build, or run commands become real.
- Review or PR conventions are selected.
- Agent expectations change.
