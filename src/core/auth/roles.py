# roles.py
from __future__ import annotations

from collections.abc import Mapping

from shared.types import JSONValue

from .settings import get_role_settings
from .utils import extract_str_values, strip_prefix


def _extend_from_nested_roles(target: list[str], source: Mapping[str, JSONValue]) -> None:
    for value in source.values():
        if isinstance(value, Mapping) and "roles" in value:
            target.extend(extract_str_values(value["roles"]))


def extract_roles(payload: Mapping[str, JSONValue]) -> list[str]:
    """Extract and normalize roles from a decoded JWT payload."""
    role_settings = get_role_settings()
    prefix = (role_settings.PREFIX or "").strip()

    roles: list[str] = []
    for key in ("roles", "groups"):
        roles.extend(extract_str_values(payload.get(key)))

    realm_access = payload.get("realm_access")
    if isinstance(realm_access, Mapping):
        roles.extend(extract_str_values(realm_access.get("roles")))

    resource_access = payload.get("resource_access")
    if isinstance(resource_access, Mapping):
        for client in resource_access.values():
            if isinstance(client, Mapping):
                roles.extend(extract_str_values(client.get("roles")))

    _extend_from_nested_roles(roles, payload)

    seen: set[str] = set()
    result: list[str] = []
    for role in roles:
        normalized = strip_prefix(role, prefix).strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
