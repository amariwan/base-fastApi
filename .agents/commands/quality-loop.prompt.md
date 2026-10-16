---
name: quality-loop
description: 'Interactive prompt to run the repo quality loop and provide targeted fixes.'
argument-hint: 'command-or-failing-output'
user-invocable: true
---

Use this prompt when tests, lint, or type checks fail.

1. Ask which command failed or paste the failing output.
2. Ask for any recent file edits to limit the search scope.
3. Propose the narrowest reproducer (single test, or single-file lint check).
4. Offer step-by-step fixes and optionally produce the exact `just` commands to run.
5. After changes, recommend the validation command to re-run.
