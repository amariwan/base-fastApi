---
name: observability
description: 'Observability for this FastAPI backend: structured logging, tracing, metrics, correlation IDs, and safe telemetry. Use when adding logs, traces, metrics, or debugging production behavior.'
argument-hint: 'area-or-symptom'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "just test-unit"
---

# Observability

Use this skill when working on observability.

## When to Use

- Structured logging, correlation IDs, tracing, metrics, safe telemetry

## Repository Rules

- Reuse `app.core.core_logging` and existing observability setup.
- Do not log secrets or sensitive payloads.
- Prefer application-owned exporters for tracing.

## Validation

- `just test-unit`
- `just lint`
