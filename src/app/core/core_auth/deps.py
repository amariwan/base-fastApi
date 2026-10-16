from __future__ import annotations

"""FastAPI dependencies for JWT authentication and RBAC."""

from collections.abc import Awaitable, Callable, Iterable, Mapping
from datetime import UTC, datetime
from typing import Annotated, NoReturn

from app.core.core_messages import MessageKeys, msg
from app.shared.types import JSONValue
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import UserClaims
from .roles import extract_groups, extract_roles, get_effective_roles
from .settings import RoleSettings, get_role_settings
from .utils import has_any
from .validators import validate_jwt

bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Security(bearer)]
RoleResolver = Callable[[RoleSettings], Iterable[str]]


def _timestamp() -> int:
    return int(datetime.now(UTC).timestamp())


def _raise_auth_error(
    detail: str,
    *,
    code: str | None = None,
    status_code: int = status.HTTP_401_UNAUTHORIZED,
) -> NoReturn:
    payload: dict[str, JSONValue] = {
        "detail": detail,
        "timestamp": _timestamp(),
    }
    if code:
        payload["error_code"] = code
    headers = {"WWW-Authenticate": "Bearer"} if status_code == status.HTTP_401_UNAUTHORIZED else None
    raise HTTPException(status_code=status_code, detail=payload, headers=headers)


def _ordered_roles(roles: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for role in roles:
        normalized = role.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def _validate_bearer_scheme(scheme: str, required: bool) -> bool:
    """Validate the authentication scheme is 'Bearer'."""
    lower_scheme = scheme.lower()
    if lower_scheme != "bearer":
        if required:
            _raise_auth_error(msg.get(MessageKeys.AUTH_UNSUPPORTED_SCHEME), code="AUTH_SCHEME_UNSUPPORTED")
        return False
    if scheme != "Bearer":
        if required:
            _raise_auth_error(msg.get(MessageKeys.AUTH_INVALID_HEADER_FORMAT), code="AUTH_INVALID_FORMAT")
        return False
    return True


def _validate_token_format(token: str, required: bool) -> bool:
    """Validate the token format (must have 3 JWT segments)."""
    if not token or " " in token:
        if required:
            _raise_auth_error(msg.get(MessageKeys.AUTH_INVALID_HEADER_FORMAT), code="AUTH_INVALID_FORMAT")
        return False

    if token.count(".") != 2:
        if not required:
            return False
        _raise_auth_error(msg.get(MessageKeys.AUTH_INVALID_TOKEN_FORMAT), code="AUTH_TOKEN_INVALID_FORMAT")
    return True


def _extract_token(request: Request, *, required: bool) -> str | None:
    raw = request.headers.get("Authorization")
    if not raw or not raw.strip():
        if required:
            _raise_auth_error(msg.get(MessageKeys.AUTH_MISSING_AUTHORIZATION_HEADER), code="AUTH_MISSING")
        return None

    scheme, _, remainder = raw.strip().partition(" ")
    if not _validate_bearer_scheme(scheme, required):
        return None

    token = remainder.strip()
    if not _validate_token_format(token, required):
        return None

    return token


_JWT_ERROR_MAP: dict[str, tuple[str, str]] = {
    "token_expired": (msg.get(MessageKeys.AUTH_TOKEN_EXPIRED), "AUTH_TOKEN_EXPIRED"),
    "token_not_yet_valid": (msg.get(MessageKeys.AUTH_TOKEN_NOT_YET_VALID), "AUTH_TOKEN_NOT_READY"),
    "token_signature_invalid": (msg.get(MessageKeys.AUTH_TOKEN_SIGNATURE_INVALID), "AUTH_TOKEN_BAD_SIGNATURE"),
    "token_audience_invalid": (msg.get(MessageKeys.AUTH_TOKEN_AUDIENCE_INVALID), "AUTH_TOKEN_BAD_AUDIENCE"),
    "token_issuer_invalid": (msg.get(MessageKeys.AUTH_TOKEN_ISSUER_INVALID), "AUTH_TOKEN_BAD_ISSUER"),
    "token_algorithm_invalid": (msg.get(MessageKeys.AUTH_TOKEN_ALGORITHM_INVALID), "AUTH_TOKEN_BAD_ALGORITHM"),
    "token_claim_missing": (msg.get(MessageKeys.AUTH_INVALID_TOKEN), "AUTH_TOKEN_INVALID"),
    "token_format_invalid": (msg.get(MessageKeys.AUTH_INVALID_TOKEN_FORMAT), "AUTH_TOKEN_INVALID_FORMAT"),
    "invalid_header": (msg.get(MessageKeys.AUTH_INVALID_HEADER_FORMAT), "AUTH_INVALID_FORMAT"),
    "alg_none_forbidden": (
        msg.get(MessageKeys.AUTH_INVALID_HEADER_FORMAT),
        "AUTH_INVALID_FORMAT",
    ),
    "invalid_token": (msg.get(MessageKeys.AUTH_INVALID_TOKEN), "AUTH_TOKEN_INVALID"),
}


def _handle_jwt_exception(exc: HTTPException) -> NoReturn:
    if exc.status_code != status.HTTP_401_UNAUTHORIZED:
        raise exc
    detail = str(exc.detail)
    message, code = _JWT_ERROR_MAP.get(detail, (msg.get(MessageKeys.AUTH_INVALID_TOKEN), "AUTH_TOKEN_INVALID"))
    _raise_auth_error(message, code=code)


def _extract_claim(payload: Mapping[str, JSONValue], *keys: str) -> str | None:
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


def _build_user(payload: Mapping[str, JSONValue], sub: str) -> UserClaims:
    return UserClaims(
        sub=sub,
        roles=extract_roles(payload),
        groups=extract_groups(payload),
        email=_extract_claim(payload, "email", "mail"),
        name=_extract_claim(payload, "name", "given_name", "family_name"),
        preferred_username=_extract_claim(payload, "preferred_username", "username"),
        organisation=_extract_claim(payload, "organisation", "org", "tenant"),
        mandant_id=_extract_claim(payload, "mandant_id", "mandantId"),
    )


async def get_current_user(request: Request, creds: Credentials) -> UserClaims:
    """Return the authenticated user or raise 401."""
    _ = creds  # ensure FastAPI documents the HTTP bearer security scheme
    token = _extract_token(request, required=True)
    if token is None:
        _raise_auth_error(msg.get(MessageKeys.AUTH_TOKEN_EXTRACTION_FAILED), code="AUTH_EXTRACTION_FAILED")
    try:
        payload = validate_jwt(token)
    except HTTPException as exc:
        _handle_jwt_exception(exc)
    sub = _extract_claim(payload, "sub")
    if not sub:
        _raise_auth_error(msg.get(MessageKeys.AUTH_INVALID_TOKEN), code="AUTH_TOKEN_INVALID")
    return _build_user(payload, sub)


async def get_optional_user(request: Request, creds: Credentials) -> UserClaims | None:
    """Return the authenticated user when present without raising errors."""
    _ = creds
    token = _extract_token(request, required=False)
    if not token:
        return None
    try:
        payload = validate_jwt(token)
    except HTTPException:
        return None
    sub = _extract_claim(payload, "sub")
    if not sub:
        return None
    return _build_user(payload, sub)


CurrentUser = Annotated[UserClaims, Depends(get_current_user)]


def require_roles(
    resolver: RoleResolver, *, detail: str = "forbidden"
) -> Callable[[UserClaims], Awaitable[UserClaims]]:
    """FastAPI dependency enforcing role-based access."""

    async def dependency(user: CurrentUser) -> UserClaims:
        cfg = get_role_settings()
        if not cfg.ACTIVE:
            return user
        required_list = _ordered_roles(resolver(cfg))
        required_set = set(required_list)
        effective = get_effective_roles(user.roles, cfg)
        if not required_set or has_any(effective, required_set):
            return user
        message = detail if detail and detail != "forbidden" else msg.get(MessageKeys.AUTH_INSUFFICIENT_PERMISSIONS)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": message,
                "required_roles": required_list,
                "user_roles": list(user.roles),
                "timestamp": _timestamp(),
            },
        )

    return dependency


require_read = require_roles(lambda cfg: cfg.READ_ROLES)
require_write = require_roles(lambda cfg: [*cfg.WRITE_ROLES, *cfg.ADMIN_ROLES])
require_delete = require_roles(lambda cfg: [*cfg.DELETE_ROLES, *cfg.ADMIN_ROLES])
require_admin = require_roles(lambda cfg: cfg.ADMIN_ROLES)
require_legal = require_admin
require_any = require_roles(lambda cfg: [*cfg.READ_ROLES, *cfg.WRITE_ROLES, *cfg.DELETE_ROLES, *cfg.ADMIN_ROLES])

__all__ = [
    "get_current_user",
    "get_optional_user",
    "get_value_from_jwt",
    "CurrentUser",
    "require_read",
    "require_write",
    "require_delete",
    "require_admin",
    "require_legal",
    "require_any",
]
