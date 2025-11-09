from __future__ import annotations

"""Authorization helpers for diagnostics endpoints."""

from collections.abc import Iterable


def is_admin(roles: Iterable[str] | None) -> bool:
    """Return True when any provided role matches the admin whitelist."""
    if not roles:
        return False
    admin_roles = {"admin", "superuser", "role_admin"}
    return any(role.lower() in admin_roles for role in roles)
