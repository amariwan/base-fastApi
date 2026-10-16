---
name: bug-fix
description: 'Interactive prompt to diagnose and fix a bug with regression coverage.'
argument-hint: 'bug-description-or-error'
user-invocable: true
---

You will guide the user through fixing a bug.

1. Ask for the failing behavior, error message, or test.
2. Ask for recent changes and affected files.
3. Propose the narrowest reproducer.
4. Identify root cause and minimal fix.
5. Add a regression test; validate with targeted command.
