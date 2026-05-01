"""UUID/id helper utilities."""

from __future__ import annotations

from uuid import uuid4


def new_id(prefix: str) -> str:
    """Generate a prefixed unique ID."""

    return f"{prefix}_{uuid4().hex}"
