---
name: caching
description: 'Caching for this FastAPI backend: in-memory/Redis caches, cache keys, invalidation, and consistency. Use when adding or changing caching behavior.'
argument-hint: 'cache-area'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "just test-unit"
---

# Caching

Use this skill when working on caching.

## When to Use

- In-memory or Redis caches, cache keys, invalidation, consistency

## Repository Rules

- Reuse `app.core.core_cache`.
- Prevent cross-tenant cache key collisions.
- Document invalidation and consistency requirements.

## Validation

- `just test-unit`
- `just lint`
