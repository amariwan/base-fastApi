# base-fastApi Launch Kit

Ready-to-use copy for promoting [amariwan/base-fastApi](https://github.com/amariwan/base-fastApi). Keep claims aligned with the current repository state when publishing.

## GitHub About

### Description

Production-minded FastAPI foundation with modular services, secure auth, async data access, optional AI infrastructure, and serious quality gates.

### Topics

```text
fastapi
python
backend
boilerplate
clean-architecture
hexagonal-architecture
sqlalchemy
pydantic
alembic
jwt-authentication
microservices
modular-monolith
ai-agents
pydantic-ai
ollama
asyncio
rest-api
uv
pytest
open-source
```

## One-line pitch

Build the business API — auth, lifecycle, storage, data access, service discovery, observability, and privacy-first AI infrastructure are already organized.

## Short launch post — English

Most FastAPI starters stop after routers, schemas, and a Dockerfile.

base-fastApi starts where the expensive backend work begins: secure JWT auth, explicit async DB lifecycle, storage and cache contracts, service discovery, health diagnostics, unified errors, and optional AI infrastructure that keeps cloud transmission disabled by default.

Start as a modular monolith. Keep extraction-ready boundaries. Add product code without rebuilding the platform around it.

https://github.com/amariwan/base-fastApi

## Short launch post — German

Die meisten FastAPI-Starter liefern Router, Schemas und ein Dockerfile. Danach beginnt die teure Arbeit.

base-fastApi bringt die Plattform bereits mit: sichere JWT-Authentifizierung, sauberer Async-DB-Lifecycle, Storage- und Cache-Verträge, Service Discovery, Health-Diagnostik, einheitliche Fehler und optionale AI-Infrastruktur — Cloud-Übertragung bleibt standardmäßig aus.

Als modularer Monolith starten. Klare Grenzen behalten. Produktlogik bauen, statt dieselbe Backend-Basis noch einmal zu erfinden.

https://github.com/amariwan/base-fastApi

## LinkedIn launch post

FastAPI makes the first endpoint easy. Building the backend around it is where teams lose weeks.

Authentication needs real verification rules. Database sessions need clear ownership. Startup and shutdown need to be deterministic. Storage, caching, email, realtime channels, health checks, and errors need stable contracts. AI integrations need explicit privacy and permission boundaries.

That is the problem base-fastApi solves.

It is a production-minded FastAPI foundation built around a reusable Core platform and feature-owned services. Teams can start with a modular monolith, keep business logic independent from frameworks and providers, and preserve a credible path to extracting services later.

The AI platform follows the same rule: disabled by default, local-first, no silent cloud fallback, bounded execution, explicit tool permissions, and secret-safe telemetry.

If you are tired of choosing between a toy scaffold and an over-engineered internal framework, take a look:

https://github.com/amariwan/base-fastApi

## Developer-community post

I wanted a FastAPI starting point that did not collapse into framework-coupled business code after the third feature.

base-fastApi now includes:

- feature-owned service boundaries;
- JWKS/HMAC JWT auth, RBAC, and resource ACLs;
- async SQLAlchemy plus Alembic for PostgreSQL, MySQL, and SQLite;
- filesystem/S3 storage, memory/Redis cache, Pub/Sub channels, and email adapters;
- lifecycle-owned startup, shutdown, health, and migration policy;
- optional PydanticAI infrastructure for inference, retrieval, agents, tools, MCP, workflows, and evals;
- Ruff, Mypy, Pyright, pytest, `uv`, `just`, and CI workflows.

The database is optional. AI is off by default. Cloud data transmission is opt-in. Product-specific decisions stay outside the platform layer.

Repository: https://github.com/amariwan/base-fastApi

## Suggested visual headline

```text
Build business APIs.
Not backend plumbing.

FastAPI · Modular Services · Secure Auth · Optional AI
```

## Call-to-action variants

- Star the repository if you want a stronger starting point for your next FastAPI service.
- Fork it for your next backend and keep the service boundaries intact.
- Review the architecture and open an issue with the first contract you would improve.
- Try the five-minute local start, then inspect the Core and service guides.
