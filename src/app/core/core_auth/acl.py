"""Linux-style Access Control List (ACL) engine.

Mirrors the classic Unix inode permission model:

Subject:   :class:`UserClaims`  — ``sub`` + ``roles`` + ``groups``
Resource:  :class:`ResourceACL` — ``owner_id``, ``group_id``,
                                   ``owner_perm``, ``group_perm``, ``other_perm``
Check:     owner → group → other  (exactly like Linux)

Permission bits
---------------
Use :class:`Perm` to compose permission requirements with ``|``:

    Perm.READ | Perm.WRITE   → requires both read and write
    Perm.RWD                 → requires full access (read + write + delete)

ACL evaluation order
--------------------
1. If ``user.sub == resource.owner_id``         → apply ``owner_perm``
2. Elif ``resource.group_id in user.groups``    → apply ``group_perm``
3. Else                                         → apply ``other_perm``

The first matching category wins — identical to how Linux resolves permissions.

FastAPI integration
-------------------
Use :func:`require_acl_perm` to protect a route with resource-level ACL::

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
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import Flag, auto
from typing import Annotated

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from .deps import CurrentUser
from .models import UserClaims

# ---------------------------------------------------------------------------
# Permission bits
# ---------------------------------------------------------------------------


class Perm(Flag):
    """Resource permission bits — compose with ``|`` just like Linux ``rwx``.

    ============  =====  ==========================================
    Constant      Value  Meaning
    ============  =====  ==========================================
    ``NONE``          0  No permissions (deny-all sentinel)
    ``READ``          1  Read access  (r)
    ``WRITE``         2  Write / modify access  (w)
    ``DELETE``        4  Delete access  (x repurposed for delete)
    ``RW``            3  Shortcut: READ | WRITE
    ``RWD``           7  Shortcut: READ | WRITE | DELETE
    ============  =====  ==========================================
    """

    NONE = 0
    READ = auto()  # 1
    WRITE = auto()  # 2
    DELETE = auto()  # 4

    # Convenience composites
    RW = READ | WRITE
    RWD = READ | WRITE | DELETE


# ---------------------------------------------------------------------------
# Resource descriptor
# ---------------------------------------------------------------------------


class ResourceACL(BaseModel):
    """ACL descriptor attached to a single resource.

    Mirrors the Linux inode permission model.  Default permissions follow
    the ``644`` convention: owner gets read+write, group and others get
    read-only.

    Attributes:
        owner_id:    ``sub`` of the resource owner.
        group_id:    Name of the owning group (must match an entry in
                     ``UserClaims.groups`` after normalisation).  ``None``
                     means the resource has no group owner — any non-owner
                     falls through directly to ``other_perm``.
        owner_perm:  Permissions granted to the owner.
        group_perm:  Permissions granted to group members.
        other_perm:  Permissions granted to everyone else.
    """

    owner_id: str
    group_id: str | None = None
    owner_perm: Perm = Perm.RW
    group_perm: Perm = Perm.READ
    other_perm: Perm = Perm.READ


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------


def check_acl(user: UserClaims, resource: ResourceACL, required: Perm) -> bool:
    """Evaluate Linux-style ACL: owner → group → other.

    Returns ``True`` when *user* holds **all** bits in *required* for
    *resource*.  The first matching category wins — identical to Linux.

    Args:
        user:     Authenticated caller.
        resource: ACL descriptor of the resource being accessed.
        required: Permission bits that must be present (e.g. ``Perm.WRITE``).

    Returns:
        ``True`` if access is granted, ``False`` otherwise.
    """
    # No permission required → always allow (avoids caller needing to special-case).
    if not required:
        return True

    # 1. Owner check — takes absolute precedence.
    if user.sub == resource.owner_id:
        return (resource.owner_perm & required) == required

    # 2. Group check — user must be a member of the resource group.
    if resource.group_id is not None:
        normalised_group = resource.group_id.strip().lower()
        if normalised_group in user.groups:  # groups are already normalised
            return (resource.group_perm & required) == required

    # 3. Other — catch-all for everyone else.
    return (resource.other_perm & required) == required


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------


def _acl_timestamp() -> int:
    return int(datetime.now(UTC).timestamp())


def require_acl_perm(
    get_resource: Callable[..., ResourceACL],
    required: Perm,
    *,
    detail: str = "Insufficient permissions on resource",
) -> Callable[..., Awaitable[UserClaims]]:
    """FastAPI dependency factory for resource-level ACL guards.

    Composes with :func:`~app.core.core_auth.deps.require_roles` — use both
    for routes that need a *global* RBAC role **and** per-resource ownership
    checks::

        @router.delete("/{doc_id}")
        async def delete_doc(
            user: UserClaims = Depends(require_admin),              # RBAC
            _acl:  UserClaims = Depends(require_acl_perm(          # ACL
                get_doc_acl, Perm.DELETE
            )),
        ):
            ...

    Args:
        get_resource: A FastAPI-injectable callable that returns a
                      :class:`ResourceACL`.  Path parameters, query parameters
                      and injected services (``Depends(…)``) are resolved
                      automatically by FastAPI.
        required:     Permission bits that the caller must hold on the resource.
        detail:       Human-readable message included in the 403 response body.

    Returns:
        An ``async`` FastAPI dependency that resolves to the authenticated
        :class:`~app.core.core_auth.models.UserClaims` on success, or raises
        ``HTTP 403`` when access is denied.
    """

    async def dependency(
        user: CurrentUser,
        resource: Annotated[ResourceACL, Depends(get_resource)],
    ) -> UserClaims:
        if not check_acl(user, resource, required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "detail": detail,
                    "required_perm": str(required),
                    "timestamp": _acl_timestamp(),
                },
            )
        return user

    return dependency


__all__ = [
    "Perm",
    "ResourceACL",
    "check_acl",
    "require_acl_perm",
]
