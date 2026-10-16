"""Pagination helpers for list responses."""

from __future__ import annotations

from app.shared.types import JSONValue

JsonDict = dict[str, JSONValue]


def paginate(items: list[JsonDict], *, limit: int, cursor: str | None) -> tuple[list[JsonDict], str | None]:
    """Simple cursor-based pagination for list responses."""

    offset = 0
    if cursor:
        if not cursor.isdigit():
            raise ValueError("cursor must be a non-negative integer string")
        offset = int(cursor)

    page_items = items[offset : offset + limit]
    next_offset = offset + limit
    next_cursor = str(next_offset) if next_offset < len(items) else None
    return page_items, next_cursor
