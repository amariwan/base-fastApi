---
name: create-service
description: 'Interactive prompt to scaffold a new FastAPI service slice under app/services.'
argument-hint: 'service-name brief-purpose'
user-invocable: true
---

You will guide the user through creating a new service package under app/services.

1. Ask for the service name and a 1-line purpose description.
2. Ask whether the service requires a database, storage, background jobs, or external APIs.
3. Ask for the minimal endpoints to create (list, get, create, update, delete) and the authentication requirements.
4. Produce a plan: list of files and folders to create (api/router.py, application/use_case.py, domain/entities.py, infrastructure/providers.py, schemas/*, tests/*).
5. Offer a runnable minimal scaffold and a list of `just` commands to validate it (unit tests and lint).
