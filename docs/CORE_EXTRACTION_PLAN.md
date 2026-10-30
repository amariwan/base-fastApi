# Core extraction: base-fastapi-core

## Decision

Extract reusable infrastructure from the application into the independently
versioned distribution `base-fastapi-core` (import package
`base_fastapi_core`). The final home is a separate GitHub
repository, `amariwan/base-fastapi-core`. First validate
package boundaries in this uv workspace; do not deploy an incomplete extraction.

## Dependency direction

- Application composition and business services may import public library APIs.
- The library must never import the application's `app.*`
  modules, business services, models, or migration scripts.
- Provider dependencies are optional when the corresponding capability is
  optional. The base installation must not require Redis, S3, DB drivers, or AI.
- Services may depend on public library contracts; the library knows no
  concrete service entrypoints.
- The application owns settings composition, route registration, startup policy,
  Alembic revisions, and database schema migration execution.

## Incremental migration phases

| Phase | Extract or change | Required proof |
| --- | --- | --- |
| 1 | Cache contract, in-memory/Redis adapters, settings, lazy factory | Independent wheel, tests, legacy import identity, lockfile |
| 2 | Storage contracts and adapters, shared JSON/errors where needed | Filesystem/S3 behavior, path traversal tests, no app imports |
| 3 | JWT validation/authorization, messages, HTTP middleware | Signature/issuer/audience checks, error envelopes, security headers |
| 4 | SQLAlchemy engine/session infrastructure | Async transaction tests, no app settings import, migrations remain in host |
| 5 | Channels, email, logging, extensibility | Lifecycle/cleanup tests and optional dependency isolation |
| 6 | Core API helpers and optional AI package | No app routes or domain schema in core; AI in separate distribution |
| 7 | Separate Git repository, tagged releases, consuming Git/package dependency | Fresh venv install, locked version, CI, compatibility smoke tests |

## Compatibility policy

Every extracted module retains its old `app.core.*` import
location as a temporary re-export. Existing public classes, call signatures,
environment variables, and behavior are preserved. Add an identity test for
re-exported symbols where callers may use `is` or runtime
type checks. Deprecation and removal require a separately approved major
release; do not remove compatibility paths during this extraction.

The extension loader currently discovers services through a hard-coded
`app.services.*` path; in its extraction phase change to
explicit registrations (and only add entry-point discovery for a real
third-party plugin requirement).

`core_users` and `alembic/versions`
must not be copied blindly into a library: the application must own model
selection and migrations. An optional identity integration can have
separately versioned migrations only after an explicit ownership decision.

## Release gates

1. Build wheel and source distribution in an isolated package environment.
2. Install the wheel in a new environment without the host application and
   import each public feature.
3. Run standalone tests and the original application tests.
4. Run Ruff, format, static typing, and import-boundary tests.
5. Check auth, schema, configuration, routes, OpenAPI, and lifecycle behavior
   for every affected slice; no implicit migration at import/request time.
6. Publish a version tag only after gates pass. Consumers pin tags or versions
   and update their lockfiles; do not depend on a moving branch in production.

## Rollback

Each migration is one focused PR. Reverting the application dependency and
compatibility re-exports restores the previous implementation. No schema or
external data is altered in Phase 1.
