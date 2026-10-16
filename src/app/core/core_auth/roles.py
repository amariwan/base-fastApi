"""Role extraction and hierarchy expansion for decoded JWT payloads."""

from __future__ import annotations

from collections.abc import Mapping

from app.shared.types import JSONValue

from .settings import RoleSettings, get_role_settings
from .utils import extract_str_values, strip_prefix

# Keys handled explicitly below — skip them during the generic nested scan
# to avoid adding the same roles twice.
_KNOWN_NESTED_KEYS: frozenset[str] = frozenset({"realm_access", "resource_access"})


def parse_hierarchy(raw: str) -> dict[str, frozenset[str]]:
    """Parse a hierarchy string into a role → effective-roles mapping.

    Syntax: ``level0>level1>level2,...``

    - ``>`` separates hierarchy levels; a role on the left **inherits** all
      roles to its right.
    - ``,`` separates **peers** within a level (no mutual inheritance).

    Example::

        "admin>editor>reader,user"
        →  admin  : {admin, editor, reader, user}
        →  editor : {editor, reader, user}
        →  reader : {reader}
        →  user   : {user}
    """
    levels: list[list[str]] = [
        [r.strip().lower() for r in level.split(",") if r.strip()] for level in raw.split(">") if level.strip()
    ]
    result: dict[str, frozenset[str]] = {}
    for i, level_roles in enumerate(levels):
        # A role inherits itself plus all roles at strictly deeper levels.
        # Peers at the same level do NOT inherit each other.
        inherited: set[str] = set()
        for deeper in levels[i + 1 :]:
            inherited.update(deeper)
        for role in level_roles:
            result[role] = frozenset({role} | inherited)
    return result


def get_effective_roles(user_roles: list[str], cfg: RoleSettings) -> set[str]:
    """Return the *effective* role set for a user after hierarchy expansion.

    If ``ROLE_HIERARCHY`` is not configured, the original role list is returned
    unchanged. Otherwise every role the user holds is expanded to include all
    roles it inherits according to the hierarchy.

    ``UserClaims.roles`` is never mutated — expansion only happens during the
    RBAC check so the JWT-sourced roles remain auditable.
    """
    if not cfg.HIERARCHY:
        return set(user_roles)
    hierarchy = parse_hierarchy(cfg.HIERARCHY)
    effective: set[str] = set()
    for role in user_roles:
        effective.add(role)
        effective.update(hierarchy.get(role, frozenset()))
    return effective


def extract_roles(payload: Mapping[str, JSONValue]) -> list[str]:
    """Extract and normalize roles from a decoded JWT payload."""
    role_settings = get_role_settings()
    prefix = (role_settings.PREFIX or "").strip()

    roles: list[str] = []

    # Top-level role arrays (Keycloak: `roles`, LDAP groups: `groups`)
    for key in ("roles", "groups"):
        roles.extend(extract_str_values(payload.get(key)))

    # Keycloak realm-level roles
    realm_access = payload.get("realm_access")
    if isinstance(realm_access, Mapping):
        roles.extend(extract_str_values(realm_access.get("roles")))

    # Keycloak client-level roles (resource_access.<client>.roles)
    resource_access = payload.get("resource_access")
    if isinstance(resource_access, Mapping):
        for client in resource_access.values():
            if isinstance(client, Mapping):
                roles.extend(extract_str_values(client.get("roles")))

    # Generic scan for any other top-level dict that carries a `roles` key,
    # skipping the keys already processed above to prevent double-counting.
    for key, value in payload.items():
        if key not in _KNOWN_NESTED_KEYS and isinstance(value, Mapping) and "roles" in value:
            roles.extend(extract_str_values(value["roles"]))

    seen: set[str] = set()
    result: list[str] = []
    for role in roles:
        normalized = strip_prefix(role, prefix).strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def extract_groups(payload: Mapping[str, JSONValue]) -> list[str]:
    """Extract and normalize group memberships from a decoded JWT payload.

    Reads the top-level ``groups`` claim (Keycloak group memberships).
    Prefix stripping is applied consistently with :func:`extract_roles`.

    The returned list is used to populate :attr:`UserClaims.groups` and
    drives the Linux-style ACL group-membership check in :mod:`acl`.
    """
    role_settings = get_role_settings()
    prefix = (role_settings.PREFIX or "").strip()

    groups_raw = extract_str_values(payload.get("groups"))

    seen: set[str] = set()
    result: list[str] = []
    for group in groups_raw:
        normalized = strip_prefix(group, prefix).strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
