---
name: storage-backend-integration
description: 'Add or modify storage backend behavior for filesystem or S3 in this repository. Use when changing app/core/core_storage, storage dependency injection, path validation, or upload and presigned URL flows.'
argument-hint: 'Describe the storage backend, path rule, or API flow to change'
user-invocable: true
---

# Storage Backend Integration

Use this skill when binary storage behavior changes in filesystem or S3-backed flows.

## When to Use
- Add or adjust storage client behavior
- Change S3 or filesystem configuration handling
- Modify dependency injection for StorageDep
- Implement upload, download, listing, delete, or presigned URL flows
- Tighten path normalization or storage error handling

## Repo-Specific Rules
- Storage abstractions live under app/core/core_storage
- Keep backend selection in the factory instead of branching across callers
- Preserve normalize_storage_path style validation and block traversal patterns
- Keep boto3 usage behind lazy import boundaries when possible
- Use the shared exceptions instead of backend-specific leak-through

## Procedure
1. Identify whether the behavior belongs in base, factory, filesystem, s3, settings, or dependency.
2. Inspect the current client interface before changing a backend implementation.
3. Keep path validation centralized and avoid duplicating safety logic.
4. Add tests for both happy path and backend-specific failure behavior.
5. Validate the narrowest storage test first before broader checks.

## Validation
- Prefer app/core/core_storage/filesystem_test.py or app/core/core_storage/s3_test.py
- Use just test-unit for backend logic changes
- Use just lint or just fix for import and formatting cleanup

## References
- app/core/core_storage/README.md
- app/core/core_storage/base.py
- app/core/core_storage/factory.py
- app/core/core_storage/filesystem.py
- app/core/core_storage/s3.py
