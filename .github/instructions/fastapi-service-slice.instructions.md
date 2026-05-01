---
description: "Use when creating or modifying Python code in this repository. Enforces strict backend structure, layering, and validation workflow conventions."
name: "Strict Python Backend Conventions"
applyTo: "**/*.py"
---
# Strict Python Backend Conventions

- Use `app` as the package root (not `src`) in imports and module paths.
- Keep edits minimal and localized to files directly related to the requested behavior.
- For service features under `app/services/<service_name>/`, preserve layer boundaries (`api`, `application`, `domain`, `infrastructure`, `schemas`, `tests`) and do not bypass them.
- Treat schema changes as migration-driven work: add Alembic revisions and do not wire implicit migration execution into request handling.
- Validate with the narrowest relevant command first, then broaden only when needed:
  - `just test-unit` for affected unit behavior
  - `just lint` for style/lint checks
  - `just mypy` for typing checks
  - `just test` for wider confidence when changes are broad
