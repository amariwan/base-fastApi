# Microservice Development Guide

> **Location:** `src/app/services/`
> **Architecture:** Feature-First · Hexagonal Architecture · Clean Architecture · Domain-Driven Design
> **Stack:** Python · FastAPI · Pydantic · SQLAlchemy · Alembic
> **Audience:** Backend Developers, AI Coding Agents, Code Reviewers
> **Status:** Architecture Standard

## 1. Purpose

This directory contains the application's independently organized business services.

Every new service must follow consistent architectural principles to ensure:

- Clear business boundaries and responsibilities
- Maintainable and testable business logic
- Separation of domain, application, transport, and infrastructure concerns
- Explicit dependencies through ports and adapters
- Reuse of existing backend infrastructure
- Consistent API contracts and error handling
- Secure data access and predictable transactions
- Independent service evolution and potential deployment
- Automated testing and architecture enforcement
- Reliable development by human engineers and AI coding agents

**Core principle: Build services around business capabilities, not technical frameworks.**

A service must own a clearly defined business responsibility.

Creating a new service must not require rebuilding authentication, database connections, logging, storage, or other capabilities already provided by the backend.

### 1.1 Architecture Model

The standard architecture combines:

| Principle              | Purpose                                                 |
| ---------------------- | ------------------------------------------------------- |
| Feature-First          | Organize code around business capabilities              |
| Clean Architecture     | Keep business logic independent of technical frameworks |
| Hexagonal Architecture | Connect external systems through ports and adapters     |
| DDD Lite               | Model business entities, value objects, and invariants  |
| Dependency Inversion   | Depend on abstractions rather than implementations      |
| Modular Monolith First | Avoid unnecessary distributed-system complexity         |
| Microservice Readiness | Preserve boundaries that support future extraction      |

A service is not automatically an independently deployable microservice simply because it has its own directory.

Two supported deployment modes are:

1. **Embedded service:** Runs inside the existing FastAPI application.
2. **Standalone microservice:** Runs as an independently deployable application with its own runtime entrypoint and deployment lifecycle.

Unless explicitly required otherwise, prefer the embedded service mode while maintaining extraction-ready boundaries.

### 1.2 Requirement Levels

- **MUST:** Mandatory architectural requirement.
- **SHOULD:** Recommended default; deviations require justification.
- **MAY:** Optional, based on actual service needs.
- **MUST NOT:** Prohibited architectural practice.

Existing functionality and public contracts must remain compatible unless a migration or breaking change is explicitly approved.

---

## 2. Repository Architecture

The backend already provides a shared technical platform.

```text
src/app/
├── asgi.py                  # Main ASGI application
├── views.py                 # Existing API composition
├── config.py                # Application configuration
│
├── core/                    # Technical platform
│   ├── core_api/
│   ├── core_auth/
│   ├── core_cache/
│   ├── core_db/
│   ├── core_extensions/
│   ├── core_logging/
│   ├── core_messages/
│   ├── core_middleware/
│   └── core_storage/
│
├── shared/                  # Shared contracts and utilities
│   ├── errors/
│   ├── exceptions/
│   ├── jobs/
│   ├── schemas/
│   ├── utils/
│   └── types.py
│
└── services/                # Business services
    ├── __init__.py
    ├── README.md
    └── <service_name>/
```

### 2.1 Ownership Rules

**`app/core/` — Technical Platform**

Contains framework integrations and shared infrastructure.

Responsibilities include database management, authentication, logging, storage, caching, middleware, and runtime functionality.

Business-specific rules do not belong in Core.

**`app/shared/` — Shared Contracts**

Contains reusable types, stable contracts, and small utilities.

Shared must not become a collection of unrelated business logic or hidden dependencies between services.

**`app/services/` — Business Capabilities**

Contains individual business services and their implementation.

Each service owns its domain logic, application use cases, and service-specific adapters.

### 2.2 Reuse Before Implementation

Before creating infrastructure, inspect existing modules.

| Requirement                       | Existing module                               |
| --------------------------------- | --------------------------------------------- |
| Authentication and identity       | `app.core.core_auth`                          |
| Database sessions and connections | `app.core.core_db`                            |
| Caching                           | `app.core.core_cache`                         |
| Structured logging                | `app.core.core_logging`                       |
| Localization and messages         | `app.core.core_messages`                      |
| Storage, filesystem, S3           | `app.core.core_storage`                       |
| HTTP middleware                   | `app.core.core_middleware`                    |
| Runtime and health endpoints      | `app.core.core_api`                           |
| Extension loading                 | `app.core.core_extensions`                    |
| Common error contracts            | `app.shared.errors` / `app.shared.exceptions` |
| Job abstractions                  | `app.shared.jobs`                             |
| Pagination and generic utilities  | `app.shared.utils`                            |

**Do not duplicate existing infrastructure inside a service.**

Inspect the actual implementation before assuming that an existing module supports a particular interface.

Infrastructure adapters may use Core implementations. Domain and Application must remain independent of concrete Core infrastructure.

---

## 3. Standard Service Structure

Every service is created under:

`src/app/services/<service_name>/`

### 3.1 Recommended Reference Structure

```text
<service_name>/
├── __init__.py
├── README.md
├── bootstrap.py                  # Service composition / dependency wiring
│
├── api/                          # Inbound HTTP adapters
│   ├── __init__.py
│   ├── router.py
│   ├── dependencies.py
│   ├── exception_handlers.py
│   ├── endpoints/
│   │   ├── create.py
│   │   ├── read.py
│   │   └── update.py
│   └── schemas/
│       ├── requests.py
│       └── responses.py
│
├── application/                  # Use cases and ports
│   ├── __init__.py
│   ├── use_cases/
│   │   ├── create.py
│   │   ├── get.py
│   │   └── update.py
│   ├── ports/
│   │   ├── repository.py
│   │   ├── unit_of_work.py
│   │   └── external_gateway.py
│   ├── dto.py
│   └── exceptions.py
│
├── domain/                       # Framework-independent business logic
│   ├── __init__.py
│   ├── entities.py
│   ├── value_objects.py
│   ├── services.py
│   ├── events.py
│   └── exceptions.py
│
├── infrastructure/               # Outbound adapters
│   ├── __init__.py
│   ├── persistence/
│   │   ├── models.py
│   │   ├── repositories.py
│   │   ├── mappers.py
│   │   └── unit_of_work.py
│   ├── clients/
│   ├── messaging/
│   ├── storage/
│   └── settings.py
│
├── contracts/                    # Optional public service contracts
│   ├── events.py
│   └── schemas.py
│
└── tests/
    ├── unit/
    │   ├── domain/
    │   └── application/
    ├── architecture/
    └── test_imports.py
```

This is a **reference architecture, not a mandatory file-generation template**.

Create only directories and modules that have a real responsibility.

Do not generate empty files or unnecessary abstractions merely to match the diagram.

### 3.2 Minimal Service Structure

For simple services, start with:

```text
<service_name>/
├── __init__.py
├── README.md
├── api/
│   ├── router.py
│   └── schemas.py
├── application/
│   └── use_cases.py
├── domain/
│   └── entities.py
├── infrastructure/
│   └── repository.py
└── tests/
    └── test_service.py
```

The exact minimal set depends on the service.

Examples:

- No persistence requirement → no repository needed.
- No external dependencies → no ports required solely for architectural symmetry.
- No HTTP endpoint → no API layer required.
- No complex domain rules → avoid artificial domain services.
- Only one small use case → a single `use_cases.py` may be sufficient.

Introduce additional modules when responsibilities become distinct.

**Prefer clear, cohesive modules over excessive fragmentation.**

---

## 4. Dependency Rules

The dependency direction must always point toward business logic.

Conceptual request flow:

```text
HTTP Request
     │
     ▼
API Layer
     │
     ▼
Application Layer
     │
     ▼
Domain Layer
```

Infrastructure dependency inversion:

```text
Application
     │
     ▼
Port / Protocol
     ▲
     │ implements
Infrastructure Adapter
     │
     ▼
Database / Storage / External API
```

The Composition Root connects concrete infrastructure adapters to application ports.

### 4.1 Allowed Dependencies

| Layer          | Allowed imports                                                             |
| -------------- | --------------------------------------------------------------------------- |
| Domain         | Python standard library and approved framework-independent domain contracts |
| Application    | Own Domain, own Ports, approved framework-independent shared contracts      |
| Infrastructure | Own Domain, Application Ports, Core infrastructure                          |
| API            | Own Application, API schemas, approved Core HTTP/Auth dependencies          |
| Contracts      | Public, stable, minimally coupled types                                     |
| Bootstrap      | Components required to assemble the service                                 |
| Tests          | Components needed to verify the tested behavior                             |

### 4.2 Forbidden Dependencies

The following dependencies are prohibited:

```text
domain         -> api
domain         -> application
domain         -> infrastructure
domain         -> FastAPI
domain         -> SQLAlchemy

application    -> api
application    -> infrastructure
application    -> concrete core_db implementations
application    -> HTTP request/response schemas

service_a      -> service_b.infrastructure
service_a      -> service_b.internal_domain
service_a      -> service_b.private_use_cases
```

Additional rules:

- Domain entities MUST NOT be SQLAlchemy ORM models.
- Use cases MUST NOT depend on FastAPI request objects.
- Application services MUST NOT raise `HTTPException`.
- Persistence models MUST NOT be exposed directly as public API contracts.
- Service-internal modules MUST NOT be treated as public integration APIs.

Enforce these boundaries with architecture tests where practical.

---

## 5. Domain Layer

**Location:** `domain/`

The Domain contains the business model and business invariants.

### Responsibilities

- Entities and Aggregate Roots
- Value Objects
- Business rules and invariants
- Domain Services
- Domain Events
- Domain Exceptions
- Business state transitions

### Rules

1. Domain code MUST be framework-independent.
2. Business invariants MUST be enforced inside the responsible domain model or service.
3. Value Objects SHOULD be immutable.
4. Domain operations MUST NOT perform direct database, filesystem, HTTP, or message-broker I/O.
5. Domain models MUST NOT import ORM models.
6. Domain behavior SHOULD be testable without dependency injection containers.
7. Domain Events describe business facts, not broker-specific messages.

### Example

For a document service:

```text
domain/
├── entities.py         # Document, DocumentVersion
├── value_objects.py    # DocumentId, DocumentStatus
├── services.py         # Document business policies
├── events.py           # DocumentPublished
└── exceptions.py       # InvalidDocumentState
```

Do not create separate folders for entities or value objects until the number of models justifies that organization.

---

## 6. Application Layer

**Location:** `application/`

Application coordinates business workflows.

### Responsibilities

- Use Cases
- Application DTOs
- Ports and interfaces
- Transaction orchestration
- Application-level authorization
- Idempotency decisions
- Coordination of domain behavior
- Application-specific errors

### 6.1 Use Case Design

A use case SHOULD represent a single meaningful business operation.

Examples:

- `CreateDocument`
- `PublishDocument`
- `GetDocument`
- `DeleteDocument`

Each use case SHOULD have:

- Explicit input and output types
- Clearly documented behavior
- Defined error conditions
- Explicit external dependencies
- Appropriate transaction boundaries
- Testable business behavior

Use cases MUST NOT know whether their repository is backed by PostgreSQL, SQLite, an external API, or an in-memory implementation.

### 6.2 Ports

Define ports from the needs of the consuming use case.

Examples:

- `DocumentRepository`
- `DocumentStorage`
- `NotificationGateway`
- `UnitOfWork`
- `Clock`

Use Python `Protocol` or abstract base classes when an actual abstraction boundary exists.

Avoid universal base repositories with unnecessary CRUD methods.

### 6.3 Commands and Queries

Separate commands and queries when complexity justifies it.

- **Commands:** Change state.
- **Queries:** Retrieve data without modifying business state.

A full CQRS implementation is not required for ordinary CRUD services.

### 6.4 Transaction Boundaries

Application defines which business operations must be atomic.

Infrastructure provides the implementation.

Use a Unit of Work when multiple operations require coordinated commit and rollback behavior.

A use case must not accidentally commit partial business changes.

---

## 7. Infrastructure Layer

**Location:** `infrastructure/`

Infrastructure implements technical interactions with external systems.

### Responsibilities

- SQLAlchemy ORM models
- Database repositories
- Unit-of-Work implementations
- External HTTP or SDK clients
- Cache adapters
- Storage adapters
- Event publishers and consumers
- Integration-specific configuration

### 7.1 Database Integration

Reuse the existing infrastructure in:

`app.core.core_db`

Relevant modules include:

- `base.py`
- `connection.py`
- `async_db_session_maker.py`
- `db_dependency.py`

Before implementation, inspect how the application creates, scopes, and closes database sessions.

Requirements:

- ORM models belong to Infrastructure.
- Domain entities must remain separate from ORM models.
- Repositories implement Application Ports.
- Data mapping must be explicit where model representations differ.
- Database transactions must have a single clearly defined owner.
- Concurrent asynchronous tasks must not share the same mutable `AsyncSession`.
- Database sessions must be released after their intended scope ends.

### 7.2 Alembic Migrations

The repository uses a central Alembic setup.

```text
alembic/
├── env.py
└── script.py.mako
```

New database models must be integrated into the existing migration metadata registration.

Before creating migrations:

1. Inspect the existing SQLAlchemy Base and metadata setup.
2. Check how Alembic discovers models.
3. Confirm table ownership and naming conventions.
4. Create or update migrations according to project conventions.
5. Review generated migrations manually.
6. Test migration execution against the target database engine.
7. Verify compatibility with existing data.

Never assume Alembic autogeneration is correct without review.

Do not automatically execute schema-changing migrations during service import.

### 7.3 External Integrations

Use `infrastructure/clients/` for third-party APIs and SDKs.

External integrations SHOULD implement Application Ports.

Requirements:

- Explicit timeouts
- Appropriate error translation
- Controlled retries with backoff
- No unbounded retry loops
- Proper resource cleanup
- Safe handling of credentials
- Idempotency for retryable write operations when applicable

### 7.4 Storage and Caching

Prefer existing modules:

- `app.core.core_storage`
- `app.core.core_cache`

Do not introduce a second storage or caching framework without a justified requirement.

Cache keys must prevent cross-tenant collisions when multi-tenancy is used.

Cache invalidation and consistency requirements must be documented.

---

## 8. API Layer

**Location:** `api/`

API is the inbound HTTP adapter.

### Responsibilities

- FastAPI routers
- Request validation
- HTTP authentication integration
- Dependency resolution
- Request-to-Application mapping
- Application-to-Response mapping
- HTTP status codes
- API error translation
- OpenAPI documentation

### 8.1 Routers

`api/router.py` is the public router entrypoint for the service.

For small services, it may contain the endpoints directly.

For larger services, it aggregates routers from `api/endpoints/`.

Router handlers SHOULD be thin.

A typical handler:

1. Receives validated request data.
2. Resolves authentication and dependencies.
3. Maps request data to an Application input.
4. Invokes one appropriate Use Case.
5. Maps the result into the response contract.

Do not implement business workflows directly inside route handlers.

### 8.2 Schemas

Use Pydantic for API transport contracts.

Place request and response schemas under:

```text
api/schemas/
├── requests.py
└── responses.py
```

Keep these models separate from:

- Domain entities
- Application DTOs
- SQLAlchemy ORM models

Do not introduce redundant DTO conversions where representations are intentionally identical and no architectural boundary is crossed.

### 8.3 API Contracts

Public endpoints MUST define:

- HTTP method and path
- Input and output schemas
- Success status
- Relevant error responses
- Authentication and authorization requirements

List endpoints SHOULD provide pagination where data volume can grow.

Sorting fields must be explicitly allowed.

Breaking API changes require an intentional migration or versioning strategy.

### 8.4 Error Handling

Map Domain and Application exceptions to HTTP errors at the API boundary.

Reuse the application's existing shared error conventions.

Inspect:

- `app.shared.errors`
- `app.shared.exceptions`
- `app.shared.schemas.errors`
- Existing global exception handlers

Do not independently register conflicting global exception handlers.

Never expose stack traces, credentials, or internal implementation details in production responses.

---

## 9. Bootstrap and Dependency Injection

**Preferred location:** `bootstrap.py`

The bootstrap module assembles the service's concrete dependencies.

It may:

- Construct use cases
- Bind ports to adapters
- Configure infrastructure dependencies
- Expose factories for API dependencies
- Coordinate service resource initialization

The existing application composition remains authoritative.

Before adding wiring, inspect:

```text
src/app/asgi.py
src/app/views.py
src/app/config.py
src/app/core/core_db/
src/app/core/core_auth/
src/app/core/core_extensions/
```

### Rules

- Do not introduce a competing global dependency-injection container.
- Prefer existing FastAPI dependency mechanisms and provider conventions.
- Request-scoped resources must remain request-scoped.
- Long-lived resources must have controlled startup and shutdown behavior.
- Module imports must not trigger unexpected database or network operations.
- Bootstrap must not contain business logic.

For simple services, a dedicated `bootstrap.py` is optional if the existing application composition already provides clean dependency wiring.

---

## 10. Registering a New Service

After implementation, connect the service to the existing application.

### Required Procedure

1. Locate the existing FastAPI application factory or instance.
2. Identify the current router registration mechanism.
3. Import and register the service's public router.
4. Reuse existing API prefixes and versioning conventions.
5. Connect required dependencies.
6. Register lifecycle resources if necessary.
7. Verify router availability.
8. Verify the generated OpenAPI schema.
9. Test application startup and shutdown.

Do not create another FastAPI application for an embedded service.

Do not create a second authentication system.

Do not duplicate middleware already installed globally.

### Standalone Deployment

If independent deployment is explicitly required, provide:

- A separate ASGI entrypoint
- Independent runtime configuration
- A deployment/build configuration
- Service-specific health and readiness endpoints
- Explicit resource lifecycle management
- Network-level integration contracts
- Independent deployment and rollback
- Defined data ownership and schema migration responsibilities

The business layers should remain reusable without depending on the main application's router registration.

---

## 11. Service-to-Service Communication

Services must communicate through explicit public interfaces.

### Allowed Patterns

- Public application contracts within the modular backend
- Consumer-defined ports and adapters
- HTTP/RPC for independently deployed services
- Integration Events for asynchronous communication

### Forbidden Patterns

- Importing another service's private repository
- Modifying another service's database tables directly
- Reusing private ORM models from another service
- Importing internal use cases without an approved public contract
- Introducing circular service dependencies

### Events

Use Domain Events for internal business events.

Use Integration Events for externally published contracts.

When publishing events must be coordinated with database changes, consider the Transactional Outbox Pattern.

Consumers should handle duplicate deliveries safely.

External events should have stable identifiers and documented schema versions.

---

## 12. Security Requirements

All services must follow the backend's existing security model.

### Authentication

Reuse `app.core.core_auth`.

Do not implement service-local token verification when equivalent supported functionality already exists.

### Authorization

Authorization must be evaluated at the appropriate business boundary.

Authentication alone is not sufficient.

The API authenticates incoming requests.

Application and Domain policies enforce relevant business permissions.

### Multi-Tenancy

For tenant-aware services:

- Derive tenant context from trusted server-side identity or authorization context.
- Never blindly trust a client-provided tenant identifier.
- Scope relevant persistence operations to the authorized tenant.
- Prevent cross-tenant data leakage.
- Use database-level protections where supported and appropriate.
- Include negative tests for tenant isolation.

### Secrets and Privacy

- No hardcoded credentials
- No secrets committed to version control
- No sensitive request data in ordinary logs
- Least-privilege access to external systems
- Explicit retention and deletion behavior when handling personal data

---

## 13. Logging, Observability, and Localization

### 13.1 Logging

Reuse:

`app.core.core_logging`

Structured logs SHOULD include available context such as:

- Service name
- Operation or use case
- Request ID
- Correlation ID
- Trace ID
- Error code
- Duration

Do not log access tokens, passwords, or sensitive payloads.

### 13.2 Observability

Production services SHOULD expose meaningful metrics and traces based on operational requirements.

Typical metrics include:

- Request count
- Error rate
- Request latency
- External dependency latency
- Database failures
- Queue processing failures

Prefer the existing application observability setup before introducing additional SDKs.

### 13.3 Localization

Reuse:

`app.core.core_messages`

The current backend includes German and English message resources.

Domain exceptions should use stable error identities rather than localized end-user strings.

Translate messages at the appropriate presentation boundary using existing project conventions.

---

## 14. Testing Strategy

Each service is responsible for testing its business behavior and integration boundaries.

The repository already uses source-adjacent `*_test.py` files and centralized tests.

Respect configured pytest discovery conventions.

### 14.1 Unit Tests

Preferred location:

`services/<service_name>/tests/unit/`

Test:

- Domain invariants
- Entity behavior
- Value Objects
- Domain Services
- Use Cases
- Authorization rules
- Application error paths

Use fakes or stubs for external dependencies.

Unit tests SHOULD NOT require a live database, server, network, or message broker.

### 14.2 Integration Tests

Preferred existing location:

`tests/integration/<service_name>/`

Test:

- Database repositories
- Real database constraints
- Transaction commit and rollback
- Infrastructure adapters
- Dependency wiring
- External integration contracts

Use the actual target database engine for behavior that depends on database-specific features.

### 14.3 End-to-End Tests

Preferred existing location:

`tests/e2e/`

Test:

- Service endpoint registration
- Authentication integration
- Authorization failures
- Valid request flows
- Error response contracts
- Relevant full-system workflows

### 14.4 Architecture Tests

Architecture tests SHOULD verify:

- Domain does not import API or Infrastructure.
- Application does not import concrete infrastructure.
- No prohibited cross-service imports exist.
- No circular dependencies exist.
- Public contracts are respected.
- Services remain importable without unintended side effects.

Consider Import Linter or equivalent tooling when compatible with the repository.

### 14.5 Verification

Before running commands, inspect:

```text
pyproject.toml
pytest.ini
pyrightconfig.json
Justfile
```

Use the existing project commands and installed tools.

Do not assume that an unverified lint, test, or type-check command is available.

**Never report a test as passing unless it was actually executed successfully.**

---

## 15. Naming Conventions

| Element         | Convention                   | Example                        |
| --------------- | ---------------------------- | ------------------------------ |
| Service package | `snake_case`                 | `document_processing`          |
| Python module   | `snake_case`                 | `create_document.py`           |
| Class           | `PascalCase`                 | `CreateDocument`               |
| Function        | `snake_case`                 | `create_document`              |
| Domain entity   | Business noun                | `Document`                     |
| Value Object    | Business value               | `DocumentId`                   |
| Use Case        | Verb + noun                  | `PublishDocument`              |
| Port            | Role-based name              | `DocumentRepository`           |
| Adapter         | Implementation-specific name | `SqlAlchemyDocumentRepository` |
| Exception       | Descriptive error name       | `DocumentNotFound`             |
| Domain Event    | Past-tense business fact     | `DocumentPublished`            |

Additional conventions:

- Use explicit names rather than generic `Manager`, `Helper`, `BaseService`, or `Common`.
- Prefer small cohesive modules.
- Keep public exports intentional.
- Avoid import-time side effects.
- Avoid circular dependencies.
- Do not create generic utility modules without a specific responsibility.

---

# AI Coding Agent Instructions

**This section is mandatory for all AI agents that create, modify, or review services.**

## 16. Agent Operating Rules

### 16.1 Read Before Writing

Before changing a service, read the applicable repository instructions and inspect the relevant code.

Minimum starting points:

```text
AGENTS.md
src/app/services/README.md

pyproject.toml
pytest.ini
pyrightconfig.json
Justfile

src/app/asgi.py
src/app/views.py
src/app/config.py

src/app/core/
src/app/shared/

alembic/env.py
```

Inspect only the relevant Core modules and supporting files in depth.

Do not read or modify unrelated modules without a concrete reason.

**Repository code is the source of truth for actual implementation behavior.**

Do not invent interfaces based on filenames or documentation assumptions.

### 16.2 Reuse Before Building

Before implementing a new feature:

1. Search for existing implementations in the repository.
2. Identify reusable Core components.
3. Inspect existing Shared contracts.
4. Search for an appropriate maintained open-source solution when external functionality is needed.
5. Evaluate compatibility, maintenance, license, and security implications.
6. Prefer the simplest suitable solution.

Do not introduce new dependencies solely because they are popular.

Do not reimplement stable existing infrastructure unnecessarily.

### 16.3 Inspect Existing Architecture

Determine:

- How the application initializes
- How services and routers are registered
- How dependencies are resolved
- How database sessions are scoped
- How Alembic registers ORM metadata
- How authentication and authorization work
- How errors are formatted
- How tests are discovered
- How resources are initialized and closed

Do not guess.

### 16.4 Design Before Implementation

Before implementing a new service, identify:

- Business responsibility
- Domain entities and invariants
- Required use cases
- Incoming and outgoing contracts
- Required ports
- Existing infrastructure to reuse
- Persistence ownership
- Security constraints
- Deployment mode
- Test strategy

Choose the minimal valid architecture.

Avoid creating unused modules or abstraction layers.

### 16.5 Implementation Rules

Agents MUST:

- Follow the dependency rules in this document.
- Preserve existing public interfaces unless explicitly instructed otherwise.
- Reuse existing infrastructure where appropriate.
- Keep Domain and Application independent of FastAPI and SQLAlchemy.
- Avoid unnecessary changes outside the target service.
- Add tests for newly introduced behavior.
- Follow existing naming and formatting conventions.
- Respect transaction and resource lifecycles.
- Avoid unrelated refactoring.
- Document meaningful architectural decisions.

Agents MUST NOT:

- Rewrite Core modules to accommodate avoidable service-specific design choices.
- Create duplicate database, auth, logging, or storage frameworks.
- Introduce circular service dependencies.
- Bypass architectural boundaries using dynamic imports.
- Add hidden runtime side effects during module import.
- Suppress type-checking or lint errors without justification.
- Remove failing tests merely to obtain a passing test suite.
- Claim completion without verification.
- Commit secrets or private credentials.

### 16.6 Incremental Changes

Prefer small, verifiable changes.

Recommended implementation order:

1. Domain models and rules
2. Application contracts and Use Cases
3. Unit tests
4. Infrastructure adapters
5. Persistence and migrations
6. API schemas and routes
7. Dependency wiring
8. Integration and E2E tests
9. Documentation and verification

Avoid implementing unrelated capabilities in a single large change.

### 16.7 Verification Before Completion

After implementation:

1. Execute relevant unit tests.
2. Execute affected integration tests.
3. Verify type checking.
4. Verify linting and formatting.
5. Validate architectural boundaries.
6. Check application startup and router registration.
7. Inspect database migrations when applicable.
8. Review changes for unrelated modifications.
9. Update the service README.

If a check cannot run, explicitly state why.

Do not represent unexecuted checks as successful.

---

## 17. Agent Completion Report

After implementing or modifying a service, provide a concise report with the following structure:

```text
STATUS
- DONE / PARTIAL / BLOCKED

SERVICE
- Name:
- Business responsibility:
- Deployment mode:

IMPLEMENTATION
- Domain:
- Application:
- Infrastructure:
- API:
- Registration:

REUSE
- Existing Core modules reused:
- Shared contracts reused:
- New dependencies:

DATABASE
- Models:
- Migration:
- Transaction behavior:

VERIFICATION
- Unit tests:
- Integration tests:
- E2E tests:
- Type checking:
- Linting:
- Architecture checks:

RISKS
- Known limitations:
- Unverified behavior:
- Follow-up tasks:
```

Only include verified results.

If the implementation is partial, make the missing pieces explicit.

---

## 18. Definition of Done

A service is complete when all applicable requirements are satisfied.

### Architecture

- [ ] Clearly defined business responsibility
- [ ] Appropriate service structure
- [ ] Domain isolated from frameworks
- [ ] Application uses explicit dependency boundaries
- [ ] Infrastructure implements required Ports
- [ ] No prohibited cross-service dependencies
- [ ] No unnecessary abstractions

### Integration

- [ ] Existing Core functionality reused
- [ ] Router registered correctly, if applicable
- [ ] Dependencies wired correctly
- [ ] Resources initialized and released correctly
- [ ] Public contracts documented

### Persistence

- [ ] ORM and Domain models separated
- [ ] Transaction boundaries defined
- [ ] Migrations reviewed, if applicable
- [ ] Database integrity constraints verified
- [ ] Data ownership defined

### Security

- [ ] Authentication integrated where required
- [ ] Business authorization enforced
- [ ] Tenant isolation verified where applicable
- [ ] Secrets handled securely
- [ ] Sensitive data excluded from logs

### Quality

- [ ] Relevant Unit Tests pass
- [ ] Relevant Integration Tests pass
- [ ] Applicable API/E2E Tests pass
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Architecture requirements verified
- [ ] README updated
- [ ] Known limitations documented

### Deployment

- [ ] Embedded or standalone deployment mode identified
- [ ] Startup and shutdown verified
- [ ] Required configuration documented
- [ ] Health/readiness behavior defined when applicable
- [ ] Independent deployment requirements verified if standalone

---

## 19. Recommended Development Workflow

```text
READ REPOSITORY RULES
        │
        ▼
INSPECT EXISTING CODE
        │
        ▼
SEARCH FOR REUSABLE COMPONENTS
        │
        ▼
DEFINE BUSINESS BOUNDARIES
        │
        ▼
CHOOSE MINIMAL SERVICE STRUCTURE
        │
        ▼
IMPLEMENT DOMAIN + APPLICATION
        │
        ▼
IMPLEMENT INFRASTRUCTURE
        │
        ▼
INTEGRATE API + DEPENDENCIES
        │
        ▼
TEST + VERIFY
        │
        ▼
DOCUMENT + REPORT
```

## 20. Final Architecture Principles

1. **Business First** — Services represent business capabilities.
2. **Domain Independence** — Business rules do not depend on frameworks.
3. **Dependency Inversion** — Use Cases depend on Ports, not concrete adapters.
4. **Reuse First** — Prefer existing Core and Shared capabilities.
5. **Explicit Contracts** — Define clear public interfaces and ownership.
6. **Security by Default** — Authentication, authorization, and data isolation are mandatory where relevant.
7. **Testability by Design** — Core business behavior must be testable in isolation.
8. **Observability by Design** — Production behavior must be diagnosable.
9. **Minimal Complexity** — Do not create layers or abstractions without a purpose.
10. **Evolutionary Architecture** — Preserve the option to deploy services independently when needed.

---

**Golden Rule**

> Build the smallest, cleanest service that satisfies the business requirements, respects architectural boundaries, reuses existing backend capabilities, and can be verified independently.

**For AI Coding Agents**

> Inspect first. Reuse before rebuilding. Design before coding. Preserve existing behavior. Verify every change. Never claim success without evidence.
