---
name: alembic-migration-flow
description: 'Create, review, or wire Alembic migrations in this repository. Use when changing database startup migration behavior, alembic config, revision generation, or runtime upgrade-to-head flow under app/core/core_db and alembic.'
argument-hint: 'Describe the migration goal or the alembic revision intent'
user-invocable: true
---

# Alembic Migration Flow

Create or review alembic migrations and wiring in this repo.

## When to Use
- Generate an autogenerate revision
- Review migration wiring for runtime upgrade-to-head flows
- Validate alembic.ini and app/core/core_db/migrations.py

## Procedure
1. Inspect alembic/env.py and app/core/core_db for migration helpers.
2. Ensure `sys.path` includes the `app` package for imports during migration.
3. Generate a revision using `uv run alembic revision --autogenerate -m "msg"` when schema changes exist.
4. Validate with a local test DB and `just test-integration` when migrations affect runtime behavior.

## Output
- Migration intent
- Files to touch
- Validation command
