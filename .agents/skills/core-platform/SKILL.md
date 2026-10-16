---
name: core-platform
description: 'Implement or review core platform capabilities: database sessions, logging, caching, storage, extensions, middleware, health, and startup checks. Use when changing src/app/core modules outside of core_auth and core_ai.'
argument-hint: 'Describe the platform change'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "just test-unit"
---

# Core Platform

Use this skill when working on `src/app/core/` (excluding `core_auth` and `core_ai`).

## When to Use

- Database sessions, connection pooling, migrations wiring
- Logging, caching, storage, extensions, middleware, health, startup checks

## Repository Rules

- `core/` must not statically import particular service implementations.
- No network connections or request-scoped sessions in global singletons at import time.
- Preserve public import surfaces via package `__init__.py`.
- Add architecture tests for boundary changes.

## Validation

- `just test-unit`
- `just lint`
