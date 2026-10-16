---
name: db-optimization
description: 'Optimize database performance. Use for slow queries and storage.'
argument-hint: 'Describe the performance issue'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, todo]
review_required: true
disabled: false
tests: "just test-unit"
---

# DB Optimization

## When to Use
- Slow queries
- Storage growth

## Steps
1. Identify slow queries.
2. Add/adjust indexes.
3. Review N+1.
4. Check bloat.

## Output
- Optimization report.
