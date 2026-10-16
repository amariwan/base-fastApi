---
name: error-handling
description: 'Error handling for this FastAPI backend: domain/application exceptions, HTTP mapping, and shared error contracts. Use when adding or changing error behavior.'
argument-hint: 'error-area'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "just test-unit"
---

# Error Handling

Use this skill when working on error handling.

## When to Use

- Domain/application exceptions, HTTP error mapping, shared error contracts

## Repository Rules

- Map domain/application exceptions to HTTP at the API boundary.
- Reuse `app.shared.errors` / `app.shared.exceptions`.
- Do not expose stack traces or secrets in production.

## Validation

- `just test-unit`
- `just lint`
