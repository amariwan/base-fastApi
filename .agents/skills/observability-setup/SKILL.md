---
name: observability-setup
description: 'Add logging, tracing, metrics. Use for new services.'
argument-hint: 'Describe the service'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, todo]
review_required: true
disabled: false
tests: "just test-unit"
---

# Observability Setup

## When to Use
- New service
- Debugging

## Steps
1. Add structured logging.
2. Add tracing spans.
3. Define metrics.
4. Verify in staging.

## Output
- Observability checklist.
