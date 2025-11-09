from __future__ import annotations

from datetime import UTC, datetime


def now_utc() -> datetime:
    """Return the current UTC datetime with tzinfo."""
    return datetime.now(UTC)


def to_comparable(value: object) -> object:
    """Return a datetime or string representation for comparison purposes."""
    if isinstance(value, datetime):
        return value
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        try:
            return iso()
        except Exception:
            return str(value)
    return str(value)


def less(lhs: object, rhs: object) -> bool:
    """Lexicographically compare two arbitrary values."""
    left = to_comparable(lhs)
    right = to_comparable(rhs)
    if isinstance(left, datetime) and isinstance(right, datetime):
        return left < right
    return str(left) < str(right)


def greater(lhs: object, rhs: object) -> bool:
    """Lexicographically compare two arbitrary values."""
    left = to_comparable(lhs)
    right = to_comparable(rhs)
    if isinstance(left, datetime) and isinstance(right, datetime):
        return left > right
    return str(left) > str(right)


def get_current_iso_timestamp() -> str:
    """Return the current UTC timestamp as ISO string."""
    return datetime.now(UTC).isoformat()
