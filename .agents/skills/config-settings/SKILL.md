---
name: config-settings
description: 'Implement or review application configuration and settings in src/app/config.py and related core settings. Use when adding settings, env vars, cached providers, or validating configuration behavior.'
argument-hint: 'Describe the config or settings change'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "just test-unit"
---

# Config Settings

Use this skill when working on configuration and settings.

## When to Use

- Add or change env vars / settings in `src/app/config.py`
- Reuse `get_app_settings()` / `get_db_settings()`
- Validate startup configuration behavior

## Repository Rules

- Do not create a second configuration system.
- Do not read or log secrets.
- Preserve backward compatibility for existing env keys.
- Document new variables in `.env.example`.

## Validation

- `just test-unit`
- `just lint`
