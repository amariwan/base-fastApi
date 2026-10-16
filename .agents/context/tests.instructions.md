---
description: 'Use when creating or modifying tests in this repository.'
name: 'Test Conventions'
applyTo: 'tests/**,**/*_test.py,**/tests/**'
---

# Test Conventions

- Do not weaken assertions or delete failing tests.
- Test behavior and failure paths, not implementation details.
- Use pytest markers (`unit`, `integration`, `e2e`).
- Respect `DB_ENABLED` defaults; keep DB-dependent tests explicit.
- Run the narrowest validation first.
