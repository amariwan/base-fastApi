# Core Authentication & Authorization

This package contains the FastAPI authentication helpers used by every API
router. It centralizes JWT validation, claim normalization, and role-based
guards so the rest of the service stays focused on business logic.

## Goals
- Enforce strict JWT validation (signature, issuer, audience, expiry).
- Provide a single `UserClaims` model for downstream dependencies.
- Keep RBAC guards declarative through `require_*` dependencies.
- Drive every security-relevant value through environment variables.

## Module Layout

```
core/auth
|-- deps.py        # FastAPI dependencies (get_current_user, require_read, ...)
|-- models.py      # Pydantic model representing normalized JWT claims
|-- roles.py       # Role extraction and normalization helpers
|-- settings.py    # Auth and role BaseSettings wrappers
|-- utils.py       # Shared helper functions
|-- validators.py  # JWT validation (JWKS + HMAC)
`-- README.md
```

## JWT Validation Flow
1. `get_current_user` reads `Authorization: Bearer <token>` and rejects missing
   headers with a 401 response.
2. `validators.validate_jwt` inspects the JOSE header and blocks `alg=none`.
3. Depending on `AUTH_MODE`, the token is verified through JWKS or HMAC. Missing
   JWKS metadata results in an HTTP 503 instead of silently bypassing checks.
4. The payload feeds into `UserClaims`, which trims values, enforces a non-empty
   `sub`, and deduplicates roles.
5. Dependencies such as `require_read` wrap `get_current_user` and fail fast
   with a 403 when the caller lacks the configured roles.

## Role Guards

| Dependency         | Purpose                                                   |
| ------------------ | --------------------------------------------------------- |
| `get_current_user` | Return authenticated `UserClaims` without enforcing RBAC. |
| `require_read`     | Requires one of `ROLE_READ_ROLES`.                        |
| `require_write`    | Requires `ROLE_WRITE_ROLES` or any admin role.            |
| `require_delete`   | Requires `ROLE_DELETE_ROLES` or any admin role.           |
| `require_admin`    | Restricts access to `ROLE_ADMIN_ROLES`.                   |

`require_roles` now accepts a resolver so role lists stay in sync with the
current `RoleSettings`. Tests can call `reload_role_settings()` to re-read the
environment without re-importing modules.

## Environment Configuration

Everything is configured via env vars. Two optional helpers keep the setup
dynamic:

| Variable                           | Description                                  |
| ---------------------------------- | -------------------------------------------- |
| `AUTH_ENV_FILE` / `AUTH_ENV_FILES` | Comma-separated env files for auth settings. |
| `ROLE_ENV_FILE` / `ROLE_ENV_FILES` | Comma-separated env files for role settings. |

Both helpers also honor `APP_ENV_FILE` and `ENV_FILE`, allowing one pointer
such as `.env.dev` to drive the entire application. Settings are lazily cached;
`reload_auth_settings()` and `reload_role_settings()` clear the cache.

Typical JWT configuration:

```
AUTH_MODE=jwks
AUTH_JWKS_URL=https://issuer/.well-known/jwks.json
AUTH_ISSUER=https://issuer/
AUTH_AUDIENCE=service
AUTH_ALGORITHMS=RS256,RS512
```

`AUTH_ALGORITHMS` accepts comma- or semicolon-separated values (or a JSON array)
and is normalized to uppercase automatically.

Role configuration:

```
ROLE_ACTIVE=true
ROLE_PREFIX=APP_
ROLE_READ_ROLES=reader,user
ROLE_WRITE_ROLES=editor
ROLE_DELETE_ROLES=editor
ROLE_ADMIN_ROLES=admin
```

## Usage Example

```python
from fastapi import APIRouter, Depends
from core.auth import UserClaims, require_write

router = APIRouter(prefix="/news")

@router.post("/")
async def create_news(
    payload: CreateNewsInput,
    user: UserClaims = Depends(require_write),
):
    ...
```

## Testing Tips
- Use `reload_auth_settings()` and `reload_role_settings()` when tests override
  environment variables.
- Feed mocked payloads through `UserClaims` to match production normalization.
- Ensure at least one test exercises each dependency (`require_read`,
  `require_write`, ...).
