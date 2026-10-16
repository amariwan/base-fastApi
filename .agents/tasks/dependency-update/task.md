# Task: Dependency Update

## Schedule
- Repeat: monthly

## Objective
Update dependencies safely and verify compatibility.

## Steps
1. Run `uv lock --upgrade` in a branch.
2. Run `just check` and `just agents-check`.
3. Review changelogs for breaking changes.
4. Update type stubs if needed.
5. Open PR with test results.

## Output
- Dependency update PR with verification summary.
