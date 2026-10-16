---
name: storage-backend-integration
description: 'Add or modify storage backend behavior for filesystem or S3 in this repository. Use when changing app/core/core_storage, storage dependency injection, path validation, or upload and presigned URL flows.'
argument-hint: 'Describe storage change and expected env/config'
user-invocable: true
---

# Storage Backend Integration

Use this skill to implement or review storage backends and upload flows.

## When to Use
- Add S3 support or change filesystem storage behavior
- Update storage dependency wiring in app/core/core_storage
- Add presigned URL flows or change path normalization

## Procedure
1. Inspect app/core/core_storage for factory, dependency, and exceptions.
2. Add or update factory providers in app/core/core_storage/factory.py.
3. Add tests under app/core/core_storage/tests for each storage backend.
4. Validate using just test-unit and just test-integration as appropriate.

## Output
- Files changed
- Minimal validation commands
