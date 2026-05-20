# ADR 0001: Build Agent-Friendly Context Docs First

## Status

Accepted

## Context

BadmFrame starts as an empty project directory for a badminton video editing application. Before choosing a framework or writing application code, the project needs a durable context layer that helps future coding agents understand the product direction, technical unknowns, and safe working habits.

Without this context, early agents may prematurely choose a stack, overbuild generic video-editor features, or lose important assumptions between sessions.

## Decision

Create an initial documentation scaffold before application implementation:

- `AGENTS.md` as the agent entry point.
- `docs/product.md` for product and MVP context.
- `docs/architecture.md` for architecture placeholders and future decisions.
- `docs/video-pipeline.md` for media workflow context.
- `docs/agent-workflow.md` for agent operating rules.
- `docs/decisions/` for ADRs.
- `tasks/` and `assets/reference/` as reserved directories for future planning and references.

## Consequences

- Future agents have a clear starting point.
- Product and technical assumptions are visible instead of hidden in chat history.
- Stack and pipeline choices remain intentionally undecided until a dedicated task resolves them.
- Documentation must be maintained as the repository becomes real code.

## Current Confirmed Content

- Documentation is the first project artifact.
- `AGENTS.md` is the top-level context entry point.
- Major technical choices should be recorded in ADRs.

## Open Questions

- What technology stack will be selected?
- What exact MVP workflow will be implemented first?
- What sample media policy should the project use?

## Agent Notes

- Do not treat this ADR as a technology decision.
- Add new ADRs for future stack, video engine, storage, and export decisions.

## Update Triggers

This ADR should usually remain stable. Add a new ADR instead of editing this one when the documentation strategy changes materially.
