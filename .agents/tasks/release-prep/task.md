# Task: Release Preparation

## Schedule
- Repeat: on-demand (before each release branch push)

## Objective
Prepare and verify a release: version bump, changelog, checks, image build.

## Steps
1. Confirm branch is `release`/`test`/`devel` and clean working tree.
2. Bump version in `pyproject.toml` (backend).
3. Update `CHANGELOG.md` with user-facing changes.
4. Run `just check` (lint, mypy, tests, coverage).
5. Run `just agents-check`.
6. Build Docker image locally and smoke-test startup (`just dev`).
7. Tag and push per `.gitlab-ci.yml` channel rules.

## Output
- Release notes draft + verification summary.
