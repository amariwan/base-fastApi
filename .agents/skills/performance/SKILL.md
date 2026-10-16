---
name: performance
description: 'Diagnose and improve performance in this FastAPI backend. Use when investigating slow endpoints, N+1 queries, caching, pagination, or resource usage.'
argument-hint: 'symptom-or-endpoint'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "just test"
---

# Performance

Use this skill when improving performance.

## When to Use

- Slow endpoints, high latency, N+1 queries, missing indexes, caching, pagination, concurrency

## Repository Rules

- Measure first; avoid premature optimization.
- Preserve behavior; focus on efficiency.
- Validate with tests or benchmarks.

## Validation

- `just test-unit`
- `just lint`
