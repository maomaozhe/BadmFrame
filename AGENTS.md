# BadmFrame Agent Guide

BadmFrame is a badminton-focused video editing application. The project is currently in the context-building stage: no application code or technology stack has been chosen yet.

This file is the entry point for coding agents. Read it first, then follow the linked documents before making changes.

## Current State

- Repository status: documentation scaffold only.
- Product direction: a video editing and annotation tool for badminton footage.
- MVP direction: help users import badminton clips, select useful moments, trim them, add simple labels or annotations, and export shareable clips.
- Technology stack: undecided.

## Recommended Reading Order

1. [Product Context](docs/product.md)
2. [Architecture Notes](docs/architecture.md)
3. [Video Pipeline](docs/video-pipeline.md)
4. [Agent Workflow](docs/agent-workflow.md)
5. [Decision Records](docs/decisions/0001-project-context-docs.md)

## Development Conventions

- Prefer small, reversible changes with clear intent.
- Keep documentation updated when a code change changes product behavior, architecture, commands, or workflow.
- Use Markdown for project context and decision records.
- Keep large binary files, especially raw videos, out of the repository unless a future policy explicitly allows them.
- Prefer realistic badminton workflows over generic video-editor assumptions.

## Do Not

- Do not introduce an application framework without recording the decision in `docs/decisions/`.
- Do not commit large media files directly to the repository.
- Do not treat BadmFrame as a generic short-video editor unless product scope changes.
- Do not overwrite user work or generated assets without checking their purpose.
- Do not remove context docs unless replacing them with a clearer structure.

## Common Commands

These are placeholders until the actual stack exists.

```bash
# install dependencies
TODO

# run local development server
TODO

# run tests
TODO

# build production artifact
TODO
```

## Current Confirmed Content

- The project starts with an agent-friendly documentation structure.
- Documentation is written in Chinese-facing project language where helpful, while commands and code identifiers remain English.
- The first implementation phase should still validate product and technical choices before writing core app code.

## Open Questions

- Which app shape should be used: desktop app, web app, or local-first hybrid?
- Which video engine should be used: FFmpeg directly, a wrapper library, or a media framework?
- Should annotation focus on text labels, court overlays, shuttle trajectory, player tags, or coaching notes first?
- Where should projects and exported clips be stored?

## Agent Notes

- Start every non-trivial task by reading this file and the most relevant linked docs.
- Add new decisions as ADRs under `docs/decisions/`.
- If you add runnable code, update the command placeholders above.
- If you add directories with durable meaning, document them in `docs/architecture.md`.

## Update Triggers

Update this file when:

- The technology stack is selected.
- Project commands become real.
- Repository structure changes.
- MVP scope changes.
- Agent workflow expectations change.
