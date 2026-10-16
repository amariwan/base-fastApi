---
name: incident-response
description: 'Triage and mitigate production incidents. Use for alerts, outages, degraded service.'
argument-hint: 'Describe the incident symptoms'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, todo]
review_required: true
disabled: false
tests: "just test-unit"
---

# Incident Response

## When to Use
- An alert fires or service degrades
- Need rapid mitigation and communication

## Steps
1. Gather symptoms, logs, metrics.
2. Determine blast radius.
3. Propose mitigation.
4. Document timeline and follow-ups.

## Output
- Incident summary and action items.
