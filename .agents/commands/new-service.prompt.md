---
name: new-service
description: 'Interactive prompt to scaffold a new FastAPI service under src/app/services.'
argument-hint: 'service-name purpose'
user-invocable: true
---

You will guide the user through creating a new service.

1. Ask for service name and 1-line purpose.
2. Ask whether DB, storage, background jobs, or external APIs are needed.
3. Ask for minimal endpoints and auth requirements.
4. Propose folder structure and files to create.
5. Offer a minimal scaffold and validation commands.
