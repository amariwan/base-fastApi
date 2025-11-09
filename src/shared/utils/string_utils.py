from __future__ import annotations


def to_camel(s: str) -> str:
    """Convert snake_case to camelCase."""
    p = s.split("_")
    return p[0] + "".join(w.title() for w in p[1:])
