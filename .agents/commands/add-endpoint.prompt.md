---
name: add-endpoint
description: 'Interactive prompt to add a new HTTP endpoint to an existing service.'
argument-hint: 'service-name endpoint-description'
user-invocable: true
---

You will guide the user through adding an endpoint.

1. Ask for service name and endpoint purpose.
2. Ask for method, path, request/response shapes, auth requirements.
3. Propose files to change (router, schemas, use case, tests).
4. Offer a minimal implementation and validation commands.
