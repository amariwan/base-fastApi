# Repository Copilot Instructions

This repository provides a set of project-specific guidelines for AI assistants and Copilot-style workflows. Follow these rules when making edits, creating files, or proposing changes.

Scope & package layout
- The repository package root is `app` (not `src`). Keep imports and PYTHONPATH aligned with `app`.
- Services live under `app/services/<service_name>/` with layers: `api`, `application`, `domain`, `infrastructure`, `schemas`, `tests`.

Coding & quality
- Use the `Justfile` tasks for validation and formatting: `just fix`, `just lint`, `just mypy`, `just test-unit`.
- Prefer minimal, localized edits. Run the narrowest validation first (unit tests or targeted lint checks) before running broader checks.
- Apply Ruff auto-fixes only when they address the reported issue. Keep diffs small and reviewable.

Tests & migrations
- Schema changes must be implemented via Alembic revisions under `alembic/` and validated using the integration migration flow.
- Do not run migrations implicitly during request handling; keep migration orchestration explicit.

Security & secrets
- Do not add credentials or secrets to the repo. CI and runtime secrets must be passed via environment/secret management.

Agent behavior guidelines
- When asked to change application behavior, ask the smallest clarifying questions necessary (service name, endpoints, DB impact).
- Prefer editing only files that are directly relevant to the requested change.
- Always recommend a focused validation command and list the exact files changed.

If you need to add skills, prompts, or agents, place them under `.github/skills/` and `.github/agents/` and include clear frontmatter and usage notes.
