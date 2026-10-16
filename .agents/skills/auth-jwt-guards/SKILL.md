---
name: auth-jwt-guards
description: 'Implement or adjust JWT validation, FastAPI auth dependencies, role guards, or ACL checks in this repository. Use when changing app/core/core_auth, require_* dependencies, role extraction, or JWKS and HMAC auth flows.'
argument-hint: 'Describe the auth flow, guard, token rule, or ACL behavior to change'
user-invocable: true
---

# Auth JWT Guards

Use this skill when a request touches authentication, authorization, or resource ACL behavior in this repository.

## When to Use
- Add or adjust JWT validation rules
- Change FastAPI dependencies like get_current_user or require_read
- Extend role extraction or claim normalization
- Implement ACL checks with owner, group, and other permissions
- Debug JWKS versus HMAC authentication behavior

## Repo-Specific Rules
- Auth code lives under app/core/core_auth
- Keep validation logic in service.py, validators.py, or deps.py instead of scattering token parsing
- Keep settings env-driven through settings.py
- Preserve the separation between RBAC roles and ACL groups
- Fail closed on malformed or unverifiable tokens

## Procedure
1. Start from the exact dependency, validator, or guard that controls the behavior.
2. Inspect models.py, roles.py, and settings.py before changing token semantics.
3. Keep HTTP-specific responses in dependencies or adapters, not in pure helper logic.
4. If ACL is involved, model the resource check explicitly through ResourceACL and Perm.
5. Add or update focused tests near the changed auth slice.
6. Validate with the narrowest auth-related unit test first.

## Validation
- Prefer app/core/core_auth/core_auth_test.py for targeted checks
- Use just test-unit for local auth changes
- Use just mypy when changing claims models or dependency signatures

## References
- app/core/core_auth/README.md
- app/core/core_auth/deps.py
- app/core/core_auth/service.py
- app/core/core_auth/acl.py
