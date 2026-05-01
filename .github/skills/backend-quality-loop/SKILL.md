---
name: backend-quality-loop
description: 'Run the repo quality loop for this FastAPI backend. Use when fixing lint, format, mypy, pyright, pytest, or dependency drift after code changes.'
argument-hint: 'Describe the failing command, file, or scope to validate'
user-invocable: true
---

# Backend Quality Loop

Use this skill for disciplined validation and cleanup in this repository.

## When to Use
- A change needs lint, format, type-check, or test validation
- A failing command needs the cheapest discriminating follow-up check
- A refactor changed paths, imports, or project configuration
- You want to tighten validation without running the broadest checks first

## Primary Commands
- just fix
- just lint
- just mypy
- just test-unit
- just test-integration
- just test-e2e
- just check

## Procedure
1. Start with the narrowest command that can falsify the current hypothesis.
2. If a failure is local, repair that exact slice before widening scope.
3. Use just fix when the issue is formatting or Ruff-driven cleanup.
4. Use just mypy for type regressions in application or infrastructure code.
5. Use just check only after narrower checks pass or when preparing a broader handoff.
6. Summarize what was validated and what remains unverified.

## Repo-Specific Notes
- The active package root is app, not src
- FastAPI dev entrypoint is app/asgi.py
- The main reusable validation path is encoded in the Justfile
- CI expects lint, mypy, tests, and image build to stay aligned

## Output Expectations
Return the exact command used, the result, and any remaining risk such as unrun integration or e2e coverage.
