"""Time-related helper utilities."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string with 'Z' suffix."""

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def utc_now_naive() -> datetime:
    """Return a naive UTC datetime (tzinfo removed).

    Use this when writing to TIMESTAMP WITHOUT TIME ZONE columns to avoid
    asyncpg errors caused by passing timezone-aware datetimes.
    """

    return datetime.now(UTC).replace(tzinfo=None)
