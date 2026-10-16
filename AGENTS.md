# AGENTS.md — Backend Engineering Rules

> **Scope:** Entire repository. **Role:** Staff-level Python/FastAPI engineer.
> **Default:** Inspect → Reuse → Plan → Implement → Verify → Report.
> **Priority:** Correctness, security, compatibility, simplicity, and evidence.

## 1. Project and Instructions

Python 3.12+ FastAPI backend using Pydantic, SQLAlchemy/AsyncSession, Alembic, `uv`, `just`, pytest, Ruff, Mypy, Pyright, Docker, and GitLab CI. Ruff targets Python 3.13; consult `pyproject.toml` for the installed/runtime version and effective settings.

- `src/app/core/`: technical platform (auth, DB, cache, extensions, logging, messages, middleware, storage, health).
- `src/app/shared/`: stable shared contracts and utilities; not a dumping ground for business logic.
- `src/app/services/<name>/`: independently organized business capabilities.
- `src/app/asgi.py`, `src/app/views.py`, `src/app/config.py`: application entrypoint, composition, and settings; inspect actual responsibilities before editing.
- `alembic/`: migrations. `tests/`: cross-service integration/E2E suites.
- **Diagrams in documentation** should always be created with the `diagram-design` skill (`.agents/skills/diagram-design`); prefer HTML/SVG/PNG outputs and keep them consistent with the repo's branding.

**When editing services, first read `src/app/services/README.md`.** Root and nested `AGENTS.md` instructions also apply according to scope. Prefer actual code and configuration to unverified documentation claims; report discrepancies rather than silently changing behavior. User/task instructions determine the requested work; never expand an analysis-only request into implementation.

## 2. Mandatory Agent Workflow

1. **Understand:** Establish requested behavior, acceptance criteria, scope, and risk (security, data, compatibility).
2. **Inspect:** Check `git status`, affected code, callers, tests, configuration, and existing architectural conventions. Use targeted searches, not broad context dumps.
3. **Reuse:** Search existing Core/Shared/service code first. Check maintained OSS options when useful; assess license, maintenance, compatibility, and security before adding dependencies. Use repository intelligence tools (e.g., ProjectAtlas/Graphify) only if installed and their indexes are current.
4. **Plan:** For nontrivial work, briefly state files, approach, dependencies, risks, and verification. Prefer small vertical slices; avoid speculative features. For trivial changes, implement directly.
5. **Baseline:** Reproduce bugs and run the smallest relevant test when feasible. Record pre-existing failures. For well-defined behavior, prefer **red → green → refactor**.
6. **Implement:** Make the smallest focused change; preserve external contracts and unrelated worktree changes. Add or update behavior-focused tests. Do not create empty architectural scaffolding.
7. **Verify:** Run targeted tests, relevant integrations, lint, types, and broader checks proportional to risk. Inspect the final diff and check for secrets, debug artifacts, and accidental edits.
8. **Report:** State `DONE`, `PARTIAL`, or `BLOCKED`; describe changes, exact checks/results, compatibility/migrations, limitations, and unverified items. Never invent test outcomes.

**Debugging:** Reproduce → observe → isolate → hypothesize → validate → fix root cause → add regression coverage → verify. Do not apply speculative fixes across unrelated modules or repeatedly rerun unchanged failing commands without a hypothesis.

**Refactoring:** Keep functional changes separate when possible. Establish behavior and test coverage first; preserve public behavior, imports, and database contracts. A file move alone is not an improvement.

## 3. Architecture — Non-negotiable Boundaries

Use feature-first organization with Clean/Hexagonal Architecture and DDD concepts **only when useful**.

```text
HTTP → API → Application → Domain
                 ↑
       Infrastructure (implements Application ports)
                 ↓
        Core / external systems
```

- **Domain:** pure business entities, value objects, invariants, domain services/events; no FastAPI, SQLAlchemy, I/O, application, or infrastructure imports.
- **Application:** use cases, orchestration, ports, business authorization, and transaction intent; imports own Domain and framework-independent contracts, **not** FastAPI, API schemas, or concrete infrastructure.
- **Infrastructure:** SQLAlchemy models, repositories, external clients, storage, messaging; implements Application ports and reuses Core technical providers.
- **API:** thin inbound adapters, Pydantic transport schemas, request/response mapping, FastAPI dependencies, HTTP error mapping; no business rules or direct persistence decisions.
- **Composition:** existing application wiring or service bootstrap binds ports to adapters; no competing global DI container or import-time I/O.
- **Cross-service:** no imports of other services' private repositories, domain internals, ORM models, or use cases. Use explicit public contracts, ports/adapters, or integration events. `core/` must not statically import particular service implementations; discovery via the loader is allowed.
- **Shared:** add only stable, truly reusable abstractions; small duplication is preferable to premature cross-service coupling.

No unnecessary `BaseRepository`, `Manager`, `Helper`, factories, or interfaces. Create optional directories only when a real responsibility exists.

### Package structure and responsibility separation

Use clear package and folder boundaries by default. When a capability contains
multiple distinct responsibilities, split it into a named package with cohesive
modules instead of growing a single broad module. For example, separate
contracts, registries, execution/runtime code, integrations/adapters, security,
observability, and tests when those responsibilities actually exist.

- Keep each module focused on one coherent responsibility and use precise names.
- Use package `__init__.py` files as the intentional public import surface; keep
  internal implementation modules replaceable.
- Organize tests into `unit/`, `integration/`, and `architecture/` packages when
  those test types exist.
- Preserve dependency direction between packages and add architecture tests for
  important boundaries.
- Do not create empty folders, placeholder modules, one-line forwarding layers,
  or artificial fragmentation merely to match a target tree.
- Small cohesive capabilities may remain a single module; split them once they
  own genuinely different concerns or become difficult to navigate and test.

### Service discovery

The documented integration entrypoint is `src/app/services/<name>/integration.py`, exposing `register_service()` with a loader-supported registration (`ServiceRegistration` or accepted mapping). Relevant registration fields may include `routers`, `startup`, `shutdown`, and `runtime_config`.

**Before implementation, inspect `src/app/core/core_extensions/loader.py`** for the actual API and supported lifecycle. Reuse discovery rather than registering the same router twice. Verify discovery, startup/shutdown, API routes, and OpenAPI where applicable.

## 4. Clean Code and Python Quality

- **KISS / YAGNI:** simplest correct implementation; no speculative abstractions or premature extensibility.
- **DRY:** deduplicate business knowledge, not every similar line; avoid forcing unrelated features into generic frameworks.
- **SOLID / SRP:** apply when they make cohesive boundaries clearer; prefer composition over inheritance.
- **Naming:** PEP 8, precise domain vocabulary, consistent names across layers. Functions describe actions; predicates read like `is_active` / `can_publish`. Avoid ambiguous `data`, `helper`, `manager` when a precise name is possible.
- **Functions:** one coherent job, explicit inputs/outputs, manageable nesting, guard clauses when clearer; avoid boolean mode switches, hidden mutation, and side effects. No arbitrary line-count rules.
- **Types:** annotate public interfaces, use precise return types, model `None`; prefer `Protocol` for meaningful ports and `dataclass` for suitable domain values. Pydantic belongs primarily at validation/transport boundaries. Do not hide type errors with unjustified `Any`, casts, ignores, or configuration changes.
- **Errors:** use meaningful domain/application exceptions, translate at boundaries, preserve causes, do not swallow unexpected failures or expose stack traces/secrets. Avoid logging and re-raising the same error at every layer.
- **Comments:** explain *why* (invariants, constraints, workarounds), not obvious *what*; keep docs accurate. Remove dead commented code; use actionable TODOs.
- **Async:** no blocking I/O in async handlers; bound concurrency, apply timeouts, propagate cancellation, close resources; never share mutable `AsyncSession` across concurrent tasks.
- **Dependencies:** prefer standard library or existing packages. Keep `pyproject.toml` and `uv.lock` in sync; add libraries only for justified needs.
- **Security:** validate at trust boundaries, enforce business authorization in use cases, isolate tenants using trusted context, protect credentials and sensitive logs, use least privilege.
- **Performance:** fix measured bottlenecks, avoid N+1 queries and unbounded list responses; use caching only with an invalidation strategy.

## 5. Database, Configuration, and Runtime

- Reuse `app.core.core_db` for engines/sessions and `app.core.core_auth`, `core_storage`, `core_cache`, `core_logging`, `core_messages` for applicable platform capabilities.
- Keep ORM models in Infrastructure, separate from Domain entities and API schemas. Define one transaction/commit owner; verify rollback paths and concurrency constraints.
- Schema changes require versioned Alembic revisions. Inspect `alembic/env.py`, review autogenerated changes, and test migrations against the target engine. **Never migrate implicitly during request handling or import.** Never run schema-changing commands against production or non-disposable DBs without authorization.
- `DB_ENABLED=false` is the documented default. DB setup may need `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE`; inspect current settings before assuming values.
- Use existing cached settings providers such as `get_app_settings()` / `get_db_settings()` when appropriate; do not create a second configuration system. Authentication supports documented `AUTH_MODE=jwks` (default) and `AUTH_MODE=hs`; inspect actual settings before changing behavior.
- Prefer existing lifespan/resource management. Never keep request-scoped sessions in global singletons or create network connections at module import.

## 6. Commands and Verification

**Inspect `Justfile`, `pyproject.toml`, `pytest.ini`, and `pyrightconfig.json` before relying on commands or quality settings.** The following commands are documented for this repository:

```bash
just dev                     # Development server, normally port 5000
just test                    # All tests
just test-unit               # Unit tests (no DB)
just test-integration        # Integration tests
just test-cov                # Coverage gate (documented: 75%)
just lint                    # Ruff lint + format check
just mypy                    # Mypy
just fix                     # Ruff auto-fix / format; review diff
just check                   # Full repository checks
just migrate "description"    # Create Alembic migration
just db-up                   # Apply migrations; verify DB target first
just test tests/e2e/test_core.py
just test -k "test_name"
```

- Tests use pytest markers `unit`, `integration`, `e2e`; check `tests/conftest.py` and configured discovery. Documented tests default to `DB_ENABLED=false`, with temporary local storage.
- Run the **smallest relevant tests first**, then appropriate unit/integration/E2E, Ruff, Mypy, Pyright, architecture tests, migrations, and startup/build checks by impact. For broad changes or full-CI claims, run `just check`.
- Ruff: documented line length 120 and target Python 3.13. Mypy: documented strict mode for application code. Pyright: documented basic mode. **Actual configuration wins.**
- Bug fixes SHOULD have regression tests; auth, tenant isolation, data integrity, or transaction bugs MUST have regression coverage or a stated blocker.
- Do not weaken test assertions, disable security scans, modify quality configuration, or delete failing tests to manufacture a pass.
- Distinguish **passed**, **failed**, **not run**, and **blocked** checks. Note pre-existing failures separately. A 75% coverage gate is not proof of correctness.

## 7. Delivery and Operational Boundaries

- Docker: documented multi-stage `uv` build on port **5000**. `SERVICE_NAME` selects/prunes services during build; `INSTALL_LIBREOFFICE=true` adds LibreOffice. Confirm Dockerfile behavior before depending on it. A filtered image alone does not establish independent microservice isolation.
- GitLab CI: documented test → lint/type → security → build → push flow, with `devel`, `test`, `release` channels. Inspect current CI configuration before editing or making claims.
- Do not force-push, reset unrelated changes, delete data, deploy, or commit unless the task authorizes that action. Do not alter production infrastructure without approval.
- Keep changes scoped; avoid formatting unrelated files, unrequested dependency updates, and unrelated refactors.
- Preserve backward compatibility; version public API/event contracts and plan expand–migrate–contract for breaking DB changes when applicable.

## 8. Definition of Done and Report Format

`DONE` requires, where applicable: acceptance criteria met; correct layer boundaries; existing Core reuse; safe auth/data handling; tested behavior and failure paths; relevant lint/type/startup checks; reviewed migrations; updated docs; final diff reviewed; no secrets or unrelated changes. Otherwise report `PARTIAL` or `BLOCKED`.

```text
STATUS: DONE | PARTIAL | BLOCKED
SUMMARY: What changed and why
FILES: Relevant paths
REUSE / DESIGN: Existing capabilities reused; key architectural decisions
VERIFICATION: Exact commands and outcomes (pass/fail/not run)
COMPATIBILITY: API, schema, configuration, migration implications
RISKS: Known issues, baseline failures, blockers, remaining work
```

**Golden rule:** Write for the next maintainer. Keep the change small, clear, secure, testable, and backed by results you actually observed.

## 9. AI Infrastructure

Reusable AI, retrieval, agent, tool, and MCP infrastructure lives in
`src/app/core/core_ai/`. Read `src/app/core/core_ai/README.md` before extending
it. Keep AI disabled and data persistence/cloud transmission off by default;
business services access Core AI from Infrastructure adapters through their own
Application ports. Do not place business prompts, product agents, customer RAG
rules, or service permissions in Core AI, and do not add public AI routes or
provider infrastructure without a concrete use case and tests.
