---
name: backend-testing
description: 'Write, fix, and refactor pytest tests for this FastAPI backend (unit, integration, E2E). Use when adding coverage, debugging failing tests, or improving test structure with fixtures, fakes, and async patterns.'
argument-hint: 'Describe the test change'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "just test"
---

# Backend Testing

Use this skill when working on tests.

## When to Use

- Add or fix pytest tests (unit, integration, E2E)
- Improve fixtures, fakes, async patterns

## Repository Rules

- Do not weaken assertions or delete failing tests.
- Test behavior and failure paths, not implementation details.
- Use pytest markers (`unit`, `integration`, `e2e`).
- Respect `DB_ENABLED` defaults.

## Validation

- `just test-unit`
- `just test`
