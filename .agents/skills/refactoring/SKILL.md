---
name: refactoring
description: 'Refactor code without changing behavior. Use for code smells and maintainability.'
argument-hint: 'Describe the target area'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, todo]
review_required: true
disabled: false
tests: "just test-unit"
---

# Refactoring

## When to Use
- Code smells or unclear boundaries
- Improve maintainability

## Steps
1. Establish test coverage.
2. Identify smells.
3. Plan slices.
4. Refactor incrementally.
5. Run checks.

## Output
- Refactor summary.
