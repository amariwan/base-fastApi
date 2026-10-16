# MCP servers for this project

Recommended Model Context Protocol (MCP) servers for this FastAPI/PostgreSQL/Redis
backend. Keep secrets in your local environment or `.env` (never commit them).

## Project-level OpenCode config snippet

Save as `opencode.json` in the repo root (or merge into your global config)
when you want to enable these servers:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "github": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-github"],
      "environment": { "GITHUB_PERSONAL_ACCESS_TOKEN": "{env:GITHUB_TOKEN}" },
      "enabled": true
    },
    "filesystem": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "."],
      "enabled": true
    },
    "git": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-git", "."],
      "enabled": true
    },
    "postgres": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-postgres", "{env:DATABASE_URL}"],
      "enabled": false
    },
    "redis": {
      "type": "local",
      "command": ["uvx", "mcp-redis"],
      "environment": { "REDIS_URL": "{env:REDIS_URL}" },
      "enabled": false
    },
    "docker": {
      "type": "local",
      "command": ["npx", "-y", "mcp-server-docker"],
      "enabled": false
    }
  }
}
```

## Enabled by default

| Server | Purpose | Requirements |
| --- | --- | --- |
| `github` | Repository, issues, PRs, CI runs | `GITHUB_TOKEN` with `repo` scope |
| `filesystem` | Read/write files in the repo | none |
| `git` | Local git history, branches, diffs | none |

## Disabled by default (enable when the local service is available)

| Server | Purpose | Enable when | Requirements |
| --- | --- | --- | --- |
| `postgres` | Inspect the application DB (schema, queries) | local Postgres running | `DATABASE_URL` |
| `redis` | Inspect Redis (cache/channels) | local Redis running | `REDIS_URL` |
| `docker` | Manage local containers | Docker daemon running | none |

## Already available via the global user config

- `supabase` — Supabase project (DB, migrations, types, logs).
- `context7` — up-to-date library documentation.
- `umbrel` — user's Umbrel instance.

## Other MCP servers worth considering for this stack

- `grafana` / `sentry` — observability and error tracking.
- `gitlab` — drive GitLab pipelines/MRs (CI runs on GitLab).
- `docker` (official Docker MCP) — alternative to `mcp-server-docker`.

## Authentication and safety

- GitHub: create a PAT at https://github.com/settings/tokens and export
  `GITHUB_TOKEN`.
- Postgres/Redis: point env vars at your local dev instance only. Never at
  production.
- Read-only by default where possible; destructive DB actions require human
  execution and two-step verification (see `AGENTS.md`).
- Do not commit real tokens or production connection strings.
