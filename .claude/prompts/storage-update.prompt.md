---
name: storage-update
description: 'Interactive prompt to change or add storage behavior (filesystem or S3).'
argument-hint: 'brief-description'
user-invocable: true
---

When used, collect these details:
1. Which backend: filesystem or s3? Provide env variables and expected bucket/path.
2. What API surface should change (upload, download, list, delete, presigned URLs)?
3. Any path normalization or access control requirements.
4. Provide a minimal test plan and the narrowest `just` command to validate the change (unit or integration).
