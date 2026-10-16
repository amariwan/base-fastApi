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
core/core_auth
|-- acl.py         # Linux-style ACL engine (Perm, ResourceACL, check_acl, require_acl_perm)
|-- deps.py        # FastAPI dependencies (get_current_user, require_read, …)
|-- keys.py        # JWKS client — key fetching and rotation (kid-based)
|-- models.py      # Pydantic model representing normalized JWT claims
|-- roles.py       # Role extraction from all Keycloak claim sources
|-- service.py     # JWTAuthService — signature validation, algorithm guards
|-- settings.py    # AuthSettings + RoleSettings (env-driven, lazily cached)
|-- utils.py       # Shared helper functions (extract_str_values, has_any, …)
|-- validators.py  # validate_jwt() — thin facade over JWTAuthService
`-- README.md
```

## JWT Validation Flow

1. `get_current_user` reads `Authorization: Bearer <token>` and rejects
   missing or malformed headers with HTTP 401.
2. The JOSE header is inspected before any key lookup:
   - `alg=none` is **always** rejected, even when signature validation is
     disabled (`AUTH_VALIDATE_SIGNATURE=false`).
   - In JWKS mode all HMAC algorithms (`HS256`, `HS384`, `HS512`) are removed
     from the allowed list to prevent algorithm-confusion attacks.
3. Depending on `AUTH_MODE`:
   - **`jwks`** — signing key is fetched from the JWKS endpoint (cached,
     rotated automatically via `kid`). An unreachable endpoint returns
     HTTP 503 instead of silently accepting tokens.
   - **`hs`** — token is verified against the HMAC secret in `AUTH_HS_SECRET`.
4. Standard claims are validated: `exp`, `nbf`, `iss`, `aud`.
   Clock-skew tolerance is configurable via `AUTH_CLOCK_SKEW_SECS`.
5. The payload feeds into `UserClaims`, which trims values, enforces a
   non-empty `sub`, and deduplicates roles.
6. Dependencies such as `require_read` wrap `get_current_user` and fail fast
   with HTTP 403 when the caller lacks the required roles.

## Role Extraction

Roles are extracted from **all** standard Keycloak claim locations and merged
into a single deduplicated list:

| Source                             | Example claim                                      |
| ---------------------------------- | -------------------------------------------------- |
| Top-level `roles` array            | `"roles": ["GRPS_Portal_Admin"]`                   |
| Top-level `groups` array           | `"groups": ["viewers"]`                            |
| `realm_access.roles`               | `"realm_access": {"roles": ["offline_access"]}`    |
| `resource_access.<client>.roles`   | `"resource_access": {"my-app": {"roles": ["editor"]}}` |

An optional prefix (`ROLE_PREFIX`) is stripped before normalization, so
`GRPS_Portal_Admin` with prefix `GRPS_` becomes `portal_admin`.

## Role Guards

| Dependency         | Required roles                              |
| ------------------ | ------------------------------------------- |
| `get_current_user` | — (authentication only, no RBAC)            |
| `require_read`     | one of `ROLE_READ_ROLES`                    |
| `require_write`    | one of `ROLE_WRITE_ROLES` **or** admin role |
| `require_delete`   | one of `ROLE_DELETE_ROLES` **or** admin role|
| `require_admin`    | one of `ROLE_ADMIN_ROLES`                   |
| `require_any`      | any role from any category                  |

`require_roles` accepts a resolver function, so custom guards can be
composed without hard-coding role names:

```python
require_protected = require_roles(lambda cfg: [*cfg.ADMIN_ROLES, *cfg.WRITE_ROLES])
```

The legacy `require_legal` dependency is now an alias for `require_admin`.

---

## Resource ACL (Linux-style)

In addition to RBAC, the module ships a **per-resource** permission engine
that mirrors the classic Unix inode model.

### Concepts

| Concept          | Description                                                   |
| ---------------- | ------------------------------------------------------------- |
| **Subject**      | `UserClaims` — `sub` + `roles` + `groups`                    |
| **Resource**     | `ResourceACL` — `owner_id`, `group_id`, `owner_perm`, `group_perm`, `other_perm` |
| **Permission**   | `Perm` flag — `READ`, `WRITE`, `DELETE`, composites `RW`, `RWD` |
| **Check order**  | owner → group → other (first match wins — exactly like Linux) |

### Perm bits

```python
class Perm(Flag):
    NONE   = 0   # no permissions
    READ   = 1   # r
    WRITE  = 2   # w
    DELETE = 4   # x (repurposed for delete)
    RW     = READ | WRITE
    RWD    = READ | WRITE | DELETE
```

### `groups` in JWT / UserClaims

The `groups` claim from the JWT token is extracted separately from `roles`
and stored in `UserClaims.groups`.  Like `roles`, its entries are:

- lowercased
- deduplicated
- stripped of the optional `ROLE_PREFIX`

RBAC (`roles`) and ACL (`groups`) are **independent** — both can be used
simultaneously on the same route.

### Default permissions (Linux 644)

`ResourceACL` defaults mirror the standard Unix 644 file permission:

| Who    | Default perm | Meaning        |
| ------ | ------------ | -------------- |
| owner  | `RW`         | read + write   |
| group  | `READ`       | read-only      |
| other  | `READ`       | read-only      |

### `check_acl` — the core function

```python
from app.core.core_auth.acl import Perm, ResourceACL, check_acl

resource = ResourceACL(
    owner_id="alice",
    group_id="editors",
    owner_perm=Perm.RWD,
    group_perm=Perm.RW,
    other_perm=Perm.READ,
)

check_acl(user_alice,   resource, Perm.DELETE)  # True  — owner
check_acl(user_bob,     resource, Perm.WRITE)   # True  — bob is in "editors"
check_acl(user_charlie, resource, Perm.WRITE)   # False — other; only READ
check_acl(user_charlie, resource, Perm.READ)    # True
```

### `require_acl_perm` — FastAPI dependency

```python
from app.core.core_auth.acl import Perm, ResourceACL, require_acl_perm

def get_doc_acl(doc_id: int, db: AsyncSession = Depends(get_db)) -> ResourceACL:
    doc = db.get(Document, doc_id)
    return ResourceACL(
        owner_id=doc.created_by,
        group_id=doc.group_id,
        owner_perm=Perm.RWD,
        group_perm=Perm.RW,
        other_perm=Perm.READ,
    )

@router.put("/{doc_id}")
async def update_doc(
    user: UserClaims = Depends(require_acl_perm(get_doc_acl, Perm.WRITE)),
):
    ...

@router.delete("/{doc_id}")
async def delete_doc(
    user: UserClaims = Depends(require_acl_perm(get_doc_acl, Perm.DELETE)),
):
    ...
```

### Combining RBAC + ACL

Use both guards together when a route needs a **global** role requirement
**and** per-resource ownership semantics:

```python
@router.delete("/{doc_id}")
async def delete_doc(
    _rbac: UserClaims = Depends(require_admin),                          # must be admin
    user:  UserClaims = Depends(require_acl_perm(get_doc_acl, Perm.DELETE)),  # must own/have delete perm
):
    ...
```

### Custom guard with ACL

```python
from app.core.core_auth.acl import check_acl, Perm, ResourceACL
from app.core.core_auth.deps import get_current_user

async def get_doc_or_403(
    doc_id: int,
    user: UserClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    doc = await db.get(Document, doc_id)
    acl = ResourceACL(owner_id=doc.created_by, group_id=doc.group_id, ...)
    if not check_acl(user, acl, Perm.READ):
        raise HTTPException(status_code=403, detail="forbidden")
    return doc
```

## Environment Configuration

### JWT / Signature

| Variable                  | Default  | Description                                           |
| ------------------------- | -------- | ----------------------------------------------------- |
| `AUTH_MODE`               | `jwks`   | `jwks` or `hs`                                        |
| `AUTH_VALIDATE_SIGNATURE` | `true`   | Set to `false` only in local dev                      |
| `AUTH_JWKS_URL`           | —        | `https://idp/.well-known/jwks.json`                   |
| `AUTH_ISSUER`             | —        | Expected `iss` claim value                            |
| `AUTH_AUDIENCE`           | —        | Expected `aud` claim value                            |
| `AUTH_ALGORITHMS`         | `RS256`  | Comma-separated; always uppercase; HS* forbidden in JWKS mode |
| `AUTH_CLOCK_SKEW_SECS`    | `60`     | Allowed time drift in seconds (max 900)               |
| `AUTH_HS_SECRET`          | —        | HMAC secret (HS mode only)                            |
| `AUTH_DISABLE_SSL_VERIFY` | `false`  | Disable TLS verification for the JWKS endpoint        |

Typical JWKS configuration (production):

```env
AUTH_MODE=jwks
AUTH_VALIDATE_SIGNATURE=true
AUTH_JWKS_URL=https://login.doamin.com/realms/TASIO/.well-known/jwks.json
AUTH_ISSUER=https://login.domain.com/realms/TASIO
AUTH_AUDIENCE=docuflowtest
AUTH_ALGORITHMS=RS256
AUTH_CLOCK_SKEW_SECS=30
```

### Role Configuration

| Variable           | Description                                                     |
| ------------------ | --------------------------------------------------------------- |
| `ROLE_ACTIVE`      | `true` to enforce RBAC; `false` to bypass all role checks       |
| `ROLE_PREFIX`      | Prefix stripped from every role before comparison               |
| `ROLE_READ_ROLES`  | Comma-separated roles that grant read access                    |
| `ROLE_WRITE_ROLES` | Comma-separated roles that grant write access                   |
| `ROLE_DELETE_ROLES`| Comma-separated roles that grant delete access                  |
| `ROLE_ADMIN_ROLES` | Comma-separated roles that grant full admin access              |

**Simple example** (generic roles, no prefix):

```env
ROLE_ACTIVE=true
ROLE_PREFIX=
ROLE_READ_ROLES=reader,user
ROLE_WRITE_ROLES=editor
ROLE_DELETE_ROLES=editor
ROLE_ADMIN_ROLES=admin
```

**Complex example** (Keycloak with `GRPS_Portal_*` naming convention):

In Keycloak the JWT payload contains role names like:

```json
"roles": [
  "GRPS_Portal_DocuFlow_Legal",
  "GRPS_Portal_DocuFlow_FachGroup",
  "GRPS_Portal_DocuFlow_Admin"
]
```

With `ROLE_PREFIX=GRPS_Portal_DocuFlow_` the prefix is stripped automatically,
so the roles become `legal`, `fachgroup`, and `admin` inside `UserClaims`.
The env config then uses only the suffix:

```env
ROLE_ACTIVE=true
ROLE_PREFIX=GRPS_Portal_DocuFlow_
ROLE_READ_ROLES=legal,fachgroup
ROLE_WRITE_ROLES=legal,fachgroup
ROLE_DELETE_ROLES=fachgroup
ROLE_ADMIN_ROLES=admin
```

Multiple roles per category are supported as a comma-separated list.
A role appearing in several categories grants the union of permissions.

> **Tip:** `require_write` and `require_delete` automatically include admin
> roles — you do not need to add `admin` to those lists explicitly.

### Role Hierarchy

`ROLE_HIERARCHY` defines an inheritance chain so that higher-level roles
automatically satisfy lower-level guards — without listing every role in
every `ROLE_*` variable.

**Syntax:** `level0>level1>level2,...`

| Operator | Meaning |
| -------- | ------- |
| `>`      | Left role **inherits** all roles to its right |
| `,`      | Peers at the **same level** — no mutual inheritance |

**Example:**

```
ROLE_HIERARCHY=admin>editor>reader,user
```

Effective role sets at runtime:

| Role in token | Effective roles (after expansion)    |
| ------------- | ------------------------------------ |
| `admin`       | `{admin, editor, reader, user}`      |
| `editor`      | `{editor, reader, user}`             |
| `reader`      | `{reader}`                           |
| `user`        | `{user}`                             |

The expansion happens **only during the RBAC check** — `UserClaims.roles`
always reflects the raw JWT claims for auditability.

**Combined with prefix stripping** (real Keycloak setup):

```env
ROLE_PREFIX=GRPS_Portal_DocuFlow_
ROLE_HIERARCHY=admin>fachgroup>legal
ROLE_READ_ROLES=legal
ROLE_WRITE_ROLES=fachgroup
ROLE_ADMIN_ROLES=admin
```

A user with `GRPS_Portal_DocuFlow_FachGroup` in their token gets:
- Prefix stripped → `fachgroup`
- Hierarchy expanded → `{fachgroup, legal}`
- Passes `require_read` and `require_write` — but **not** `require_admin`

### Optional env-file helpers

| Variable                           | Description                                  |
| ---------------------------------- | -------------------------------------------- |
| `AUTH_ENV_FILE` / `AUTH_ENV_FILES` | Comma-separated env files for auth settings. |
| `ROLE_ENV_FILE` / `ROLE_ENV_FILES` | Comma-separated env files for role settings. |

Both helpers also honor `APP_ENV_FILE` and `ENV_FILE`. Settings are lazily
cached; `reload_auth_settings()` and `reload_role_settings()` clear the cache.

## Usage Examples

**Protect a route with a specific permission level:**

```python
from fastapi import APIRouter, Depends
from app.core.core_auth import UserClaims, require_write, require_admin

router = APIRouter(prefix="/resource")

@router.post("/")
async def create_resource(
    payload: CreateResourceInput,
    user: UserClaims = Depends(require_write),
):
    ...

@router.delete("/{id}")
async def delete_resource(
    id: int,
    user: UserClaims = Depends(require_admin),
):
    ...
```

**Custom role guard:**

```python
from app.core.core_auth.deps import require_roles

# Grant access to users who have at least one of the legal or admin roles
require_legal_or_admin = require_roles(
    lambda cfg: [*cfg.READ_ROLES, *cfg.ADMIN_ROLES],
    detail="Requires legal or admin role",
)

@router.get("/sensitive")
async def sensitive_data(user: UserClaims = Depends(require_legal_or_admin)):
    ...
```

**Read a claim without failing the request:**

```python
from app.core.core_auth.deps import get_value_from_jwt, Credentials

@router.get("/info")
async def info(locale: str | None = Depends(lambda c: get_value_from_jwt("locale", c))):
    ...
```

## Testing Tips

- Use `reload_auth_settings()` and `reload_role_settings()` when tests
  override environment variables.
- Feed mocked payloads through `UserClaims` to match production normalization.
- See `core_auth_test.py` for reference: RSA key generation, JWKS mocking,
  `alg=none` rejection, algorithm-confusion tests, hierarchy expansion, and
  RBAC dependency tests.
- To test a protected route end-to-end, set `AUTH_VALIDATE_SIGNATURE=false`
  and pass a plain (unsigned) token — or mock `validate_jwt` directly.
