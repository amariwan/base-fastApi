from __future__ import annotations

"""FastAPI dependencies for JWT authentication and RBAC."""

from collections.abc import Awaitable, Callable, Iterable
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import UserClaims
from .roles import extract_roles
from .settings import RoleSettings, get_role_settings
from .utils import has_any
from .validators import validate_jwt

bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Security(bearer)]
RoleResolver = Callable[[RoleSettings], Iterable[str]]


def _extract_claim(payload: dict[str, object], *keys: str) -> str | None:
    """Return the first non-empty string value for the provided claim keys."""
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


async def get_value_from_jwt(key: str, creds: Credentials) -> str | None:
    """Return a claim value from the JWT without failing the request."""
    if not creds:
        return None
    try:
        payload = validate_jwt(creds.credentials)
    except HTTPException:
        return None
    value = payload.get(key)
    if isinstance(value, str):
        return value.strip() or None
    return str(value) if value is not None else None


def _build_user(payload: dict[str, object], sub: str) -> UserClaims:
    return UserClaims(
        sub=sub,
        roles=extract_roles(payload),
        email=_extract_claim(payload, "email", "mail"),
        name=_extract_claim(payload, "name", "given_name", "family_name"),
        preferred_username=_extract_claim(payload, "preferred_username", "username"),
        organization=_extract_claim(payload, "organisation", "org", "tenant"),
        mandant_id=_extract_claim(payload, "mandant_id"),
    )


async def get_current_user(creds: Credentials) -> UserClaims:
    """Return the authenticated user or raise 401."""
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = validate_jwt(creds.credentials)
    sub = _extract_claim(payload, "sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sub_missing")
    return _build_user(payload, sub)


async def get_optional_user(creds: Credentials) -> UserClaims | None:
    """Return the authenticated user when present without raising errors."""
    if not creds:
        return None
    try:
        payload = validate_jwt(creds.credentials)
        sub = _extract_claim(payload, "sub")
        if not sub:
            return None
        return _build_user(payload, sub)
    except HTTPException:
        return None


def _normalize_required(roles: Iterable[str]) -> set[str]:
    return {role.strip().lower() for role in roles if role.strip()}


CurrentUser = Annotated[UserClaims, Depends(get_current_user)]


def require_roles(
    resolver: RoleResolver, *, detail: str = "forbidden"
) -> Callable[[UserClaims], Awaitable[UserClaims]]:
    """FastAPI dependency enforcing role-based access."""

    async def dependency(user: CurrentUser) -> UserClaims:
        cfg = get_role_settings()
        if not cfg.ACTIVE:
            return user
        required = _normalize_required(resolver(cfg))
        if not required or has_any(user.roles, required):
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

    return dependency


require_read = require_roles(lambda cfg: cfg.READ_ROLES)
require_write = require_roles(lambda cfg: [*cfg.WRITE_ROLES, *cfg.ADMIN_ROLES])
require_delete = require_roles(lambda cfg: [*cfg.DELETE_ROLES, *cfg.ADMIN_ROLES])
require_admin = require_roles(lambda cfg: cfg.ADMIN_ROLES)
require_any = require_roles(
    lambda cfg: [*cfg.READ_ROLES, *cfg.WRITE_ROLES, *cfg.DELETE_ROLES, *cfg.ADMIN_ROLES]
)

__all__ = [
    "get_current_user",
    "get_optional_user",
    "get_value_from_jwt",
    "require_read",
    "require_write",
    "require_delete",
    "require_admin",
    "require_any",
]
