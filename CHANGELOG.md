# Changelog

All notable changes to this template are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-10-17

### Added
- `compose.yml` dev stack (Postgres, Redis, Mailhog, MinIO) matching `.env.example`.
- `just init` / `just init-db` recipes for one-command onboarding.
- `hello` reference service (`src/app/services/hello`) demonstrating the service pattern.
- Unit tests for the hello service's pure logic (`tests/unit/`).
- Architecture boundary tests (`tests/architecture/test_boundaries.py`).
- `VERSION` file and this changelog.
- Tutorial: `docs/Development_Setup/adding-a-service.md`.

### Notes
- Core module toggles (`API_ENABLED`, `AUTH_ENABLED`, ...) already exist in `AppSettings`
  and are honoured by `create_app()`; no new toggle work was needed.