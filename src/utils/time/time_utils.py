from __future__ import annotations

from datetime import UTC, datetime


def _utc_now_naive() -> datetime:
    """Return current UTC datetime without tzinfo (naive) for DB comparisons."""
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_datetime(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def _is_published_at_reached(
    published_at: datetime | None, *, reference_time: datetime | None = None
) -> bool:
    if published_at is None:
        return False
    pub = _normalize_datetime(published_at)
    ref = reference_time or _utc_now_naive()
    return bool(pub and pub <= ref)


def _is_visible_until_reached(
    visible_until: datetime | None, *, reference_time: datetime | None = None
) -> bool:
    if visible_until is None:
        return False
    vis = _normalize_datetime(visible_until)
    ref = reference_time or _utc_now_naive()
    return bool(vis and vis <= ref)
