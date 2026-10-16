# Task: Daily Code Review

## Schedule
- Repeat: daily (cron: 0 9 * * *)

## Objective
Review the previous day's changes for correctness, security, and style.

## Scope
- `src/app/` and `tests/`
- Changed files since last run (`git log --since="1 day ago"`)

## Steps
1. Collect changed files.
2. Run `just lint` and `just mypy`.
3. Run targeted tests for affected modules.
4. Summarize findings and open follow-up issues.

## Output
- Markdown report in `.agents/memories/` or linked PR comment.
