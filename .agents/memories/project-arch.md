# Persistent Memory: Project Architecture

## Stack
- Python 3.12+ FastAPI backend
- SQLAlchemy (async) + Alembic migrations
- PostgreSQL (optional, DB_ENABLED), Redis (cache/channels)
- uv, just, pytest, ruff, mypy, pyright

## Key directories
- `src/app/core/` — platform (auth, db, cache, storage, channels, email, logging)
- `src/app/shared/` — shared contracts/utilities
- `src/app/services/<name>/` — business capabilities
- `alembic/` — migrations
- `tests/` — cross-service integration/E2E

## Conventions
- Feature-first, Clean/Hexagonal architecture.
- Application ports/adapters; no cross-service private imports.
- Alembic revisions only; never migrate in request/import.

## Notes
- Update this file when architecture decisions change.
