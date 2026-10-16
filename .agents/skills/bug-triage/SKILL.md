---
name: bug-triage
description: 'Triage and classify bugs. Use for incoming issues.'
argument-hint: 'Describe the bug'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, todo]
review_required: true
disabled: false
tests: "just test-unit"
---

# Bug Triage

## When to Use
- New bug report
- Regression

## Steps
1. Reproduce.
2. Classify severity.
3. Assign owner.
4. Define regression test plan.

## Output
- Triage summary.
