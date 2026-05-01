---
name: ci-pipeline-summary
description: 'Brief summary and quick mapping of repository CI to GitHub Actions. Use for small migrations or to explain pipeline responsibilities.'
argument-hint: 'Describe the pipeline area to summarize (tests, quality, build, security)'
user-invocable: true
---

# CI Pipeline Summary

This skill summarizes the repository's CI intent and maps GitLab CI jobs to GitHub Actions jobs.

## When to Use
- Port a small GitLab CI job to GitHub Actions
- Explain which job runs tests, lint, security audits, or image builds
- Identify required secrets for Docker push or registry access

## Typical Job Mapping
- `backend:test` -> `test` job (runs `just test -m "unit or integration or e2e"`)
- `backend:quality` -> `quality` job (runs `just lint`, `just mypy-report`)
- `backend:security` -> `security` job (exports locked requirements and runs `pip-audit`)
- `backend:build:*` -> `build-*` jobs (docker build + artifact upload)

## Required repository secrets
- CI_REGISTRY and CI_REGISTRY_PASSWORD for Docker push
- Any cloud credentials needed for integration tests (DB, S3 endpoints, etc.)

## Output
Return a compact mapping, a list of files to change, and the minimal validation commands for the new workflow.
