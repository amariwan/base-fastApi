---
name: api-design
description: 'Design RESTful APIs for this FastAPI backend: resource modeling, HTTP methods, status codes, versioning, pagination, and error responses.'
argument-hint: 'endpoint-or-resource'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "just test-unit"
---

# API Design

Use this skill when designing or changing API contracts.

## When to Use

- New endpoints, resource modeling, status codes, versioning, pagination, error responses

## Repository Rules

- Keep handlers thin; delegate to use cases.
- Preserve external contracts; plan expand-migrate-contract for breaking changes.
- Update OpenAPI metadata and tests.

## Validation

- `just test-unit`
- `just lint`
