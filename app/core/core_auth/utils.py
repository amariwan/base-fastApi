"""Shared auth helpers independent from FastAPI."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast


def extract_str_values(value: object) -> list[str]:
    """Return trimmed non-empty strings from a scalar or iterable value."""
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, Iterable):
        return [
            stripped
            for item in cast(Iterable[object], value)
            if not isinstance(item, list | dict) and (stripped := str(item).strip())
        ]
    return []


def strip_prefix(text: str, prefix: str) -> str:
    """Remove *prefix* from *text*, case-sensitively first, then case-insensitively."""
    if not prefix:
        return text
    if text.startswith(prefix):
        return text[len(prefix) :]
    if text.lower().startswith(prefix.lower()):
        return text[len(prefix) :]
    return text


def has_any(user_roles: Iterable[str], required: Iterable[str]) -> bool:
    """Return ``True`` if *user_roles* and *required* share at least one role."""
    normalised_user = {r.strip().lower() for r in user_roles if r.strip()}
    normalised_required = {r.strip().lower() for r in required if r.strip()}
    return not normalised_user.isdisjoint(normalised_required)
