# `.agents/` — Agent & Skill Configuration

This directory contains repository-specific agent definitions, skills, prompts,
instructions, and governance policy used by AI coding assistants.

## Structure

```text
.agents/
├── README.md
├── main.yaml        # Manifest: what this project uses
├── agents/          # Named subagents for specific roles (*.agent.md)
├── skills/          # What agents can DO (*/SKILL.md)
├── commands/        # Reusable single-shot tasks (*.prompt.md)
├── context/         # What agents need to KNOW (instructions, mcp config)
├── permissions/     # What agents are ALLOWED to do (STRICT_AGENT_POLICY.md)
├── tasks/           # Repeatable tasks (task.md per task)
└── memories/        # Persistent memory (project-arch.md, ...)
```

## Governance

All files under `.agents/agents/` and `.agents/skills/` MUST comply with
`.agents/permissions/STRICT_AGENT_POLICY.md`, including required YAML frontmatter:
`name`, `description`, `owner`, `allowed_tools`, `review_required`, `disabled`, `tests`.

Validate with:

```bash
python .agents/tools/validate_agents.py
# or
just agents-check
```

## Usage

- Agent definitions describe a specialist role, constraints, approach, and output format.
- Skills describe a reusable workflow or domain capability.
- Prompts are interactive entry points for common tasks.
- Instructions apply automatically to matching file paths.

## Source of Truth

`.agents/` is the canonical location for OpenCode/Codex-style agent configuration.
`.github/` contains the Copilot-specific equivalents. Keep both in sync; when in
doubt, update `.agents/` first and mirror to `.github/`.

## Safety

- No secrets or production data in any file.
- Least-privilege `allowed_tools`; extensions require maintainer review.
- Destructive actions require human execution and two-step verification.

## Agents

| Agent | Purpose |
| --- | --- |
| api-contract-engineer | API transport contracts, schemas, routers, OpenAPI |
| auth-access-engineer | JWT auth, dependencies, RBAC/ACL |
| config-settings-engineer | Configuration and settings |
| core-ai-engineer | Core AI infrastructure |
| core-platform-engineer | Core platform capabilities |
| db-migration-operator | Alembic migrations and DB wiring |
| fastapi-architect | FastAPI feature work and architecture |
| quality-investigator | Lint/type/test failures |
| service-slice-engineer | Business service slices |
| storage-integration-engineer | Filesystem/S3 storage |
| test-engineer | Pytest tests |
| incident-responder | Incident triage and mitigation |
| refactor-specialist | Behavior-preserving refactoring |
| feature-developer | End-to-end feature development |
| bug-triager | Bug triage and classification |
| api-designer | API contract design and review |
| db-optimizer | Database performance optimization |
| observability-engineer | Logging, tracing, metrics |
| test-coverage-engineer | Test coverage improvement |
| docs-writer | Documentation updates |

## Skills

See `.agents/skills/*/SKILL.md`. Notable: `core-ai`, `config-settings`, `core-platform`, `api-contracts`, `backend-testing`, `fastapi-service-slice`, `storage-backend-integration`, `auth-jwt-guards`, `alembic-migration-flow`, `backend-quality-loop`.
