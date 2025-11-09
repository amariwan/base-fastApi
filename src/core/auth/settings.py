from __future__ import annotations

"""Authentication and role settings with lazy caching."""

import os
from collections.abc import Iterable
from functools import lru_cache

from pydantic import Field, HttpUrl, SecretStr, StrictBool, StrictInt, StrictStr, field_validator
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
            "AUTH_ENV_FILE", "AUTH_ENV_FILES", "APP_ENV_FILE", "ENV_FILE", default=(".env",)
        ),
        env_prefix="AUTH_",
        extra="ignore",
        case_sensitive=False,
    )

    MODE: StrictStr = Field(default="jwks", description="jwks | hs")
    VERIFY_SIGNATURE: bool = True
    VERIFY_EXP: bool = True
    VERIFY_ISS: bool = True
    VERIFY_AUD: bool = True
    CLOCK_SKEW_SECS: StrictInt = Field(default=60, ge=0, le=900)

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


class RoleSettings(BaseSettings):
    """Role-based access configuration."""

    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(
            "ROLE_ENV_FILE", "ROLE_ENV_FILES", "APP_ENV_FILE", "ENV_FILE", default=(".env",)
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

    @field_validator("READ_ROLES", "WRITE_ROLES", "DELETE_ROLES", "ADMIN_ROLES", mode="before")
    @classmethod
    def _parse_roles(cls, value: object) -> list[str]:
        if value is None:
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
