from __future__ import annotations

"""Authentication and role settings with lazy caching."""

import os
from collections.abc import Iterable
from functools import lru_cache

from pydantic import (
    Field,
    HttpUrl,
    SecretStr,
    StrictInt,
    StrictStr,
    ValidationInfo,
    field_validator,
)
from pydantic_core import PydanticUndefined
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_env_values(raw: str) -> list[str]:
    """Split comma/semicolon separated values into a cleaned list."""
    cleaned = raw.replace(";", ",")
    return [entry.strip() for entry in cleaned.split(",") if entry.strip()]


def _resolve_env_files(*var_names: str, default: tuple[str, ...]) -> tuple[str, ...]:
    """Return env file paths based on the first non-empty variable."""
    files: list[str] = []
    for name in var_names:
        raw = os.getenv(name)
        if raw:
            files.extend(_split_env_values(raw))
    if not files:
        return default
    seen: list[str] = []
    for path in files:
        if path not in seen:
            seen.append(path)
    return tuple(seen)


class AuthSettings(BaseSettings):
    """Environment-driven authentication configuration."""

    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(
            "AUTH_ENV_FILE",
            "AUTH_ENV_FILES",
            "APP_ENV_FILE",
            "ENV_FILE",
            default=(".env",),
        ),
        env_prefix="AUTH_",
        extra="ignore",
        case_sensitive=False,
    )

    MODE: StrictStr = Field(default="jwks", description="jwks | hs")
    VALIDATE_SIGNATURE: bool = Field(default=True, description="Enable full JWT signature validation")
    VERIFY_SIGNATURE: bool = True
    VERIFY_EXP: bool = True
    VERIFY_ISS: bool = True
    VERIFY_AUD: bool = True
    DISABLE_SSL_VERIFY: bool = False
    CLOCK_SKEW_SECS: StrictInt = Field(default=60, ge=0, le=900)

    @field_validator("CLOCK_SKEW_SECS", mode="before")
    @classmethod
    def _parse_clock_skew_secs(cls, value: object) -> object:
        """Allow numeric strings from environment (e.g. '60') to be accepted.

        The field is declared as StrictInt which rejects str input even when it
        represents a number. Convert common string forms to int here so the
        downstream strict validation succeeds.
        """
        if value is None or value == "":
            return 60
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError as err:
                raise TypeError("CLOCK_SKEW_SECS must be an integer") from err
        # let Pydantic raise an appropriate error for unsupported types
        return value

    ISSUER: StrictStr | None = None
    AUDIENCE: StrictStr | None = None
    ALGORITHMS: list[StrictStr] | StrictStr = Field(default_factory=lambda: ["RS256"])

    JWKS_URL: HttpUrl | None = None
    HS_SECRET: SecretStr | None = None

    @field_validator("ALGORITHMS", mode="before")
    @classmethod
    def _parse_algorithms(cls, value: object) -> list[str]:
        if value is None or value == "":
            return ["RS256"]
        if isinstance(value, str):
            return _normalize_algorithms(value.replace(";", ",").split(","))
        if isinstance(value, Iterable):
            return _normalize_algorithms(value)
        raise TypeError("ALGORITHMS must be string or iterable")

    @field_validator("ALGORITHMS", mode="after")
    @classmethod
    def _ensure_algorithms(cls, value: list[str]) -> list[str]:
        return value or ["RS256"]


def _is_missing(value: object) -> bool:
    if value is None or value is PydanticUndefined:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list | tuple | set | dict):
        return len(value) == 0
    return False


def _legacy_env_value(*names: str) -> str | None:
    for name in names:
        if not name:
            continue
        raw = os.getenv(name)
        if raw and raw.strip():
            return raw.strip()
    return None


_LEGACY_ROLE_ENV_MAP: dict[str, tuple[str, ...]] = {
    "READ_ROLES": ("ROLES_READ",),
    "WRITE_ROLES": ("ROLES_WRITE",),
    "DELETE_ROLES": ("ROLES_DELETE",),
    "ADMIN_ROLES": ("ROLES_ADMIN",),
}


class RoleSettings(BaseSettings):
    """Role-based access configuration."""

    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(
            "ROLE_ENV_FILE",
            "ROLE_ENV_FILES",
            "APP_ENV_FILE",
            "ENV_FILE",
            default=(".env",),
        ),
        env_prefix="ROLE_",
        extra="ignore",
        case_sensitive=False,
    )

    ACTIVE: bool = True
    PREFIX: StrictStr = ""
    READ_ROLES: list[StrictStr] = Field(default_factory=list)
    WRITE_ROLES: list[StrictStr] = Field(default_factory=list)
    DELETE_ROLES: list[StrictStr] = Field(default_factory=list)
    ADMIN_ROLES: list[StrictStr] = Field(default_factory=list)
    HIERARCHY: StrictStr | None = Field(
        default=None,
        description=(
            "Optional role-inheritance chain. "
            "Syntax: 'admin>editor>reader,user' — '>' means left inherits right, "
            "','' separates peers at the same level. "
            "Example result: admin→{admin,editor,reader,user}, editor→{editor,reader,user}."
        ),
    )

    @field_validator("ACTIVE", mode="before")
    @classmethod
    def _fallback_active(cls, value: object) -> object:
        if not _is_missing(value):
            return value
        legacy = _legacy_env_value("ROLES_ACTIVE")
        return legacy if legacy is not None else value

    @field_validator("PREFIX", mode="before")
    @classmethod
    def _fallback_prefix(cls, value: object) -> object:
        if not _is_missing(value):
            return value
        legacy = _legacy_env_value("ROLE_PREFIX", "ROLES_PREFIX", "AUTH_ROLE_PREFIX")
        return legacy if legacy is not None else value

    @field_validator("READ_ROLES", "WRITE_ROLES", "DELETE_ROLES", "ADMIN_ROLES", mode="before")
    @classmethod
    def _parse_roles(cls, value: object, info: ValidationInfo) -> list[str]:
        if _is_missing(value):
            field_name = info.field_name or ""
            for env_name in _LEGACY_ROLE_ENV_MAP.get(field_name, ()):
                legacy = _legacy_env_value(env_name)
                if legacy is not None:
                    value = legacy
                    break
        if value is None or value is PydanticUndefined:
            return []
        if isinstance(value, str):
            entries = value.replace(";", ",").split(",")
            return [entry.strip().lower() for entry in entries if entry.strip()]
        if isinstance(value, Iterable):
            return [str(entry).strip().lower() for entry in value if str(entry).strip()]
        raise TypeError("Roles must be provided as string or iterable")


@lru_cache(maxsize=1)
def _cached_auth_settings() -> AuthSettings:
    return AuthSettings()


@lru_cache(maxsize=1)
def _cached_role_settings() -> RoleSettings:
    return RoleSettings()


def get_auth_settings() -> AuthSettings:
    """Return the cached AuthSettings instance."""
    return _cached_auth_settings()


def get_role_settings() -> RoleSettings:
    """Return the cached RoleSettings instance."""
    return _cached_role_settings()


def reload_auth_settings() -> AuthSettings:
    """Reload AuthSettings (handy for tests)."""
    _cached_auth_settings.cache_clear()
    return _cached_auth_settings()


def reload_role_settings() -> RoleSettings:
    """Reload RoleSettings (handy for tests)."""
    _cached_role_settings.cache_clear()
    return _cached_role_settings()


def _normalize_algorithms(value: Iterable[object]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for alg in value:
        candidate = str(alg or "").strip().upper()
        if candidate and candidate not in seen:
            seen.add(candidate)
            normalized.append(candidate)
    return normalized


__all__ = [
    "AuthSettings",
    "RoleSettings",
    "get_auth_settings",
    "get_role_settings",
    "reload_auth_settings",
    "reload_role_settings",
]
