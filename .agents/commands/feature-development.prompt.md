---
name: feature-development
description: 'Interactive prompt to plan and implement a feature slice in this backend.'
argument-hint: 'feature-description'
user-invocable: true
---

You will guide the user through implementing a feature.

1. Ask for the feature goal and owning service.
2. Ask about DB, storage, jobs, external APIs, and auth requirements.
3. Identify the minimal files to change (api, application, domain, infrastructure, tests).
4. Propose a step-by-step plan with validation commands.
5. After implementation, recommend `just test-unit`, `just lint`, `just mypy`.
