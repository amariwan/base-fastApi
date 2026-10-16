---
name: backend-patterns
description: 'Backend architecture patterns for this FastAPI service: layering, ports/adapters, transactions, caching, and service boundaries.'
argument-hint: 'pattern-or-area'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "just test-unit"
---

# Backend Patterns

Use this skill when applying backend architecture patterns.

## When to Use

- Service layering, ports/adapters, transactions, caching, boundaries

## Repository Rules

- Respect dependency direction (API → Application → Domain; Infrastructure implements ports).
- Reuse existing Core/Shared capabilities.
- Keep services cohesive and extraction-ready.

## Validation

- `just test-unit`
- `just lint`
