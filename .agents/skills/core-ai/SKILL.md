---
name: core-ai
description: 'Implement or review AI, retrieval, agent, tool, and MCP infrastructure under src/app/core/core_ai. Use when changing core AI modules, providers, prompts, retrieval, or tests, or when wiring AI capabilities from services through application ports.'
argument-hint: 'Describe the core AI change or review scope'
user-invocable: true
owner: team/backend
allowed_tools: [read, search, edit, execute]
review_required: true
disabled: false
tests: "uv run pytest -q src/app/core/core_ai/tests"
---

# Core AI

Use this skill when working on `src/app/core/core_ai/`.

## When to Use

- Add or modify providers, models, routing, inference, streaming, structured output
- Work on embeddings, knowledge, retrieval, vector stores
- Change agent definitions, runtime, tools, permissions, approvals, MCP
- Modify workflows, checkpoints, memory, observability, evaluations

## Repository Rules

- Read `src/app/core/core_ai/README.md` first.
- Keep AI disabled by default; no import-time network calls.
- Business prompts/agents belong in services, not Core AI.
- Add architecture tests for boundary changes.
- Validate with `uv run pytest -q src/app/core/core_ai/tests`.

## Validation

- `uv run pytest -q src/app/core/core_ai/tests`
- `uv run ruff check src/app/core/core_ai`
- `uv run mypy src/app/core/core_ai`
