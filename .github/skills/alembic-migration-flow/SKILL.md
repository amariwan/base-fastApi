---
name: alembic-migration-flow
description: 'Create, review, or wire Alembic migrations in this repository. Use when changing database startup migration behavior, alembic config, revision generation, or runtime upgrade-to-head flow under app/core/core_db and alembic.'
argument-hint: 'Describe the migration, schema change, or startup behavior to add or adjust'
user-invocable: true
---

# Alembic Migration Flow

Use this skill when schema migration behavior or migration automation changes in this repository.

## When to Use
- Add or inspect Alembic revision flow
- Change runtime migration startup behavior
- Update alembic.ini or alembic/env.py wiring
- Review upgrade-to-head logic in application startup
- Align database path changes with migration commands and settings

## Repo-Specific Rules
- Migration config lives in alembic.ini and alembic/
- Runtime migration helpers live in app/core/core_db/migrations.py
- Keep sync database URL wiring explicit for Alembic
- Prefer existing Justfile migration commands over ad hoc shell snippets
- Avoid hiding schema changes outside explicit revisions

## Procedure
1. Start from the concrete schema change, revision, or startup migration hook.
2. Inspect alembic/env.py and app/core/core_db/migrations.py before editing wiring.
3. Keep migration execution isolated from request-path code.
4. If startup behavior changes, check app/core/startup_checks.py and app/views.py.
5. Validate with the narrowest migration-related command or focused test available.

## Validation
- Use the repo tasks for migration and tests when possible
- Prefer just test-integration for DB-touching flow changes
- Use just mypy when changing migration helper signatures or settings access

## References
- alembic/env.py
- app/core/core_db/migrations.py
- app/core/startup_checks.py
- Justfile
