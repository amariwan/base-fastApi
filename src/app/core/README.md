# Core Architecture

`app.core` is the backend's internal platform layer. It provides reusable
contracts and infrastructure for authentication, persistence, storage, HTTP
middleware, localization, extensions, and diagnostics. Feature services may
depend on core modules; core modules must not import feature services.

## Module map

| Module | Responsibility | Main boundary |
| --- | --- | --- |
| `core_api` | Core HTTP routes, schemas, and pure diagnostic formatting | FastAPI routes stay thin |
| `core_auth` | JWT identity, role authorization, and ACL checks | Auth dependencies expose normalized claims |
| `core_ai` | Optional AI providers, inference, retrieval, agents, MCP, and evaluations | Lazy, internal, policy-controlled; no public router |
| `core_cache` | Small in-process TTL cache | No backend abstraction without a second real backend |
| `core_channels` | Optional in-process or Redis Pub/Sub for WebSockets | No channel connection until explicitly enabled and requested |
| `core_db` | SQLAlchemy base, URLs, sessions, and migration coordination | Session/engine ownership is explicit |
| `core_email` | Direct SMTP/console delivery plus optional Celery enqueueing | Queue failures fall back to direct delivery |
| `core_extensions` | Service discovery, registration, and lifecycle hooks | Registration is deterministic and observable |
| `core_logging` | Logging adapters, formatting, and journey diagnostics | Provider code uses stdlib-compatible loggers |
| `core_messages` | Message catalogs and request locale resolution | Missing startup catalogs are configuration errors |
| `core_middleware` | Composable HTTP middleware registration | Middleware does not orchestrate business services |
| `core_storage` | Provider-independent file storage contract and providers | Callers use `StorageClient`, not SDKs |
| `core_users` | Local email identity model, password hashing, and user lifecycle | UserManager flushes; calling use case owns commit |
| `startup_checks.py` | Startup probes and migration orchestration | Invoked by the application lifespan |

## Dependency rules

The preferred direction is:

```text
contracts / value objects
        -> application-facing providers and dependencies
        -> infrastructure implementations
        -> framework adapters and application wiring
```

`core_api.health_diagnostics` illustrates the same rule for HTTP diagnostics:
it formats typed results and startup states but does not register routes or run
probes. `core_storage` illustrates the infrastructure boundary. `protocols.py` owns the provider-
independent contract, `paths.py` owns logical path validation, and
`filesystem.py`, `s3.py`, and `google_cloud_storage.py` implement the contract.
Provider SDK types must not leak into service/application code. `base.py` is a
small compatibility module for legacy imports; new code should import from
`protocols` or `paths` directly.

## Configuration and lifecycle

Settings are validated through the existing Pydantic settings providers and
cached where the application requires process-scoped configuration. Factories
must remain lazy when a provider has an optional SDK. Database and service
startup are run by the FastAPI lifespan; importing a module should not create
network connections or start background work.

Database migration inspection and advisory-lock execution live in
`core_db.startup_migrations`; `startup_checks.py` coordinates those operations
with health probes and the configured fail-open/fail-closed policy.

## Error handling

Each module owns its expected runtime errors. Infrastructure providers translate
provider-specific failures into module exceptions while preserving the cause
with `raise ... from exc`. Programming errors and unexpected failures must not
be silently swallowed. Startup probes may convert failures into diagnostics
because degraded startup is an explicit application setting.

## Public API rules

Import from a package's `__init__.py` for stable application-facing symbols,
for example:

```python
from app.core.core_storage import StorageClient, StorageDep
```

Concrete providers, settings internals, and compatibility modules are not the
preferred application API. Any compatibility shim must stay small and be
covered by tests.

## Testing strategy

- Pure contracts and value transformations use focused unit tests.
- Provider behavior uses provider-specific tests and shared contract cases
  where the observable semantics are interchangeable.
- FastAPI dependencies, middleware, and routes use focused application tests.
- Changes are verified in the repository devcontainer with the narrowest
  affected test first, followed by Ruff/Pyright and broader checks as risk
  requires.

## Adding a storage provider

1. Implement `StorageClient` in a provider module.
2. Normalize logical paths before constructing provider keys.
3. Use `KeyNamespace` for provider prefixes.
4. Translate provider-specific not-found and operation failures into
   `StorageError` subclasses.
5. Add provider tests for upload, download, existence, deletion, listing,
   metadata, and URL behavior.
6. Add one lazy factory branch and update the storage documentation.

## Anti-patterns

Do not add a generic `core/utils.py`, a dependency container, or a base service
class without a demonstrated cross-module contract. Do not import a concrete
storage SDK from feature/application code, create engines at import time, or
hide lifecycle failures behind broad exception handlers.
