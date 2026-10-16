---
name: refactor
description: 'Interactive prompt to refactor code safely with preserved behavior.'
argument-hint: 'refactor-target'
user-invocable: true
---

You will guide the user through a safe refactor.

1. Ask for the target and desired outcome.
2. Ask for existing tests and coverage.
3. Propose small, verifiable steps.
4. Preserve public behavior, imports, and DB contracts.
5. Validate with tests and lint after each step.
