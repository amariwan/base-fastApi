---
name: service-slice
description: 'Interactive prompt to scaffold or extend a FastAPI service slice under src/app/services.'
argument-hint: 'service-name slice-description'
user-invocable: true
---

You will guide the user through creating or extending a service slice.

1. Ask for service name and purpose.
2. Ask whether DB, storage, jobs, or external APIs are needed.
3. Propose minimal files/folders (api, application, domain, infrastructure, schemas, tests).
4. Offer a runnable scaffold and validation commands.
