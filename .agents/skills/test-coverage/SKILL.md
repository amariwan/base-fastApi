---
name: test-coverage
description: 'Improve test coverage. Use for gaps and quality gates.'
argument-hint: 'Describe the target area'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, todo]
review_required: true
disabled: false
tests: "just test-unit"
---

# Test Coverage

## When to Use
- Coverage gaps
- Quality gates

## Steps
1. Run coverage.
2. Add tests.
3. Remove flaky tests.
4. Re-run gate.

## Output
- Coverage delta.
