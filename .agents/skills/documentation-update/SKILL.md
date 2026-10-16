---
name: documentation-update
description: 'Update documentation. Use for README and docs.'
argument-hint: 'Describe the doc change'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, todo]
review_required: true
disabled: false
tests: "just lint"
---

# Documentation Update

## When to Use
- After feature/fix
- Outdated docs

## Steps
1. Identify outdated docs.
2. Update README/docs.
3. Regenerate OpenAPI if needed.
4. Review clarity.

## Output
- Docs summary.
