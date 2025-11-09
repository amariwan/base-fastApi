from __future__ import annotations

"""Small helpers for normalized environment variable parsing."""

import os
from collections.abc import Iterable


def read_env_bool(name: str, *, default: bool = False) -> bool:
    """Return a boolean flag parsed from an environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def read_env_csv(name: str, *, default: Iterable[str] = ()) -> list[str]:
    """Parse a comma/semicolon separated env var into a list of trimmed values."""
    raw = os.getenv(name)
    if raw is None:
        return list(default)
    cleaned = raw.replace(";", ",")
    return [value.strip() for value in cleaned.split(",") if value.strip()]


def first_env(*names: str, default: str = "") -> str:
    """Return the first non-empty env var from the provided candidates."""
    for name in names:
        raw = os.getenv(name)
        if raw:
            return raw
    return default
