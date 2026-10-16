---
name: api-contracts
description: 'Design and review API transport contracts: Pydantic schemas, routers, request/response mapping, status codes, and OpenAPI. Use when changing HTTP endpoints, schemas, or public API behavior in src/app.'
argument-hint: 'Describe the API contract change'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "just test-unit"
---

# API Contracts

Use this skill when working on HTTP transport contracts.

## When to Use

- Add or change routers, Pydantic schemas, request/response mapping
- Preserve external contracts; plan expand-migrate-contract for breaking changes

## Repository Rules

- Keep handlers thin: validate, map, delegate, map errors.
- No business rules or persistence decisions in handlers/schemas.
- Update OpenAPI-relevant metadata and tests.

## Validation

- `just test-unit`
- `just lint`
