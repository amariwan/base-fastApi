"""Central toggles for optional core modules."""

from __future__ import annotations

import os

_DEFAULT_DISABLED = {"db", "channels", "ai"}

CORE_NAMES = (
    "api",
    "auth",
    "ai",
    "cache",
    "channels",
    "db",
    "email",
    "extensions",
    "logging",
    "messages",
    "middleware",
    "storage",
    "users",
)


def _short(name: str) -> str:
    return name.lower().removeprefix("core_").strip()


def _env_truthy(value: str | None) -> bool | None:
    if value is None:
        return None
    stripped = value.strip().lower()
    if stripped == "":
        return None
    if stripped in {"1", "true", "yes", "on", "enabled"}:
        return True
    if stripped in {"0", "false", "no", "off", "disabled"}:
        return False
    return None


def is_core_enabled(name: str) -> bool:
    short = _short(name)

    disabled_raw = (
        os.getenv("DISABLED_CORES")
        or os.getenv("CORES_DISABLED")
        or os.getenv("DISABLE_CORES")
        or os.getenv("DISABLED_CORE_MODULES")
        or ""
    )
    disabled = {item.strip().lower() for item in disabled_raw.replace(",", " ").split() if item.strip()}
    if short in disabled or f"core_{short}" in disabled:
        return False

    legacy_map = {
        "db": "DB_ENABLED",
        "channels": "CHANNELS_ENABLED",
        "ai": "AI_ENABLED",
        "cache": "CACHE_ENABLED",
        "storage": "STORAGE_ENABLED",
        "email": "EMAIL_ENABLED",
        "auth": "AUTH_ENABLED",
        "logging": "LOGGING_ENABLED",
        "messages": "MESSAGES_ENABLED",
        "middleware": "MIDDLEWARE_ENABLED",
        "api": "API_ENABLED",
        "extensions": "EXTENSIONS_ENABLED",
        "users": "USERS_ENABLED",
    }

    candidates = [
        f"CORE_{short.upper()}_ENABLED",
        f"{short.upper()}_ENABLED",
    ]
    legacy = legacy_map.get(short)
    if legacy:
        candidates.append(legacy)

    for var in candidates:
        value = _env_truthy(os.getenv(var))
        if value is not None:
            return value

    return short not in _DEFAULT_DISABLED


def enabled_cores() -> list[str]:
    return [name for name in CORE_NAMES if is_core_enabled(name)]


def disabled_cores() -> list[str]:
    return [name for name in CORE_NAMES if not is_core_enabled(name)]


__all__ = ["CORE_NAMES", "disabled_cores", "enabled_cores", "is_core_enabled"]
