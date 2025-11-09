from __future__ import annotations

"""Shared auth helpers independent from FastAPI."""

from collections.abc import Iterable


def extract_str_values(value: object) -> list[str]:
    """Return trimmed string representations from supported containers."""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Iterable):
        result: list[str] = []
        for item in value:
            if isinstance(item, list | dict):
                continue
            text = str(item).strip()
            if text:
                result.append(text)
        return result
    return []


def strip_prefix(text: str, prefix: str) -> str:
    """Remove a prefix from the provided text if present."""
    if not prefix or not text.startswith(prefix):
        return text
    return text[len(prefix) :]


def has_any(user_roles: Iterable[str], required: Iterable[str]) -> bool:
    """Return True if any user role matches the required roles."""
    user_set = {role.strip().lower() for role in user_roles if role.strip()}
    required_set = {role.strip().lower() for role in required if role.strip()}
    return bool(user_set & required_set)
