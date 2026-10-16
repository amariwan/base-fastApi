---
name: fastapi-service-slice
description: 'Create or extend a FastAPI service slice in this repository. Use when adding routers, use cases, schemas, provider wiring, or tests under app/services.'
argument-hint: 'Describe the service name and the slice to add or change'
user-invocable: true
---

# FastAPI Service Slice

Use this skill when a change belongs inside a service package under app/services.

## When to Use
- Add a new service package under app/services
- Extend an existing service with a router, schema, use case, or provider
- Keep service-layer boundaries intact while implementing a feature
- Add tests for a service slice without mixing domain, API, and infrastructure concerns

## Repository Rules
- New services live under app/services/<service_name>/
- Keep layers separate: api, application, domain, infrastructure, schemas, tests
- Put shared code in app/shared instead of coupling services together
- Keep __init__.py minimal
- Use the existing app wiring pattern instead of inventing a parallel bootstrap flow

## Procedure
1. Identify the target service and the exact slice to change.
2. Inspect the nearest existing implementation in the same service or a neighboring service.
3. Place HTTP concerns in api, orchestration in application, rules in domain, and IO in infrastructure.
4. Register routers and providers through the existing service loading flow rather than ad hoc imports.
5. Add or update tests close to the changed slice.
6. Run the narrowest validation first, then expand to lint or type-check only if needed.

## Validation
- Use just test-unit for co-located unit tests
- Use just test-integration for cross-layer flows
- Use just lint or just fix when formatting or lint errors appear
- Use just mypy for typing-sensitive changes

## References
- Service architecture: app/services/README.md
- App entrypoint: app/views.py
- Service loading: app/core/core_extensions/loader.py
