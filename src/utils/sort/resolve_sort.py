from __future__ import annotations

"""Dynamic ordering helpers for SQLAlchemy queries."""

from sqlalchemy import ColumnElement
from sqlalchemy.orm.attributes import InstrumentedAttribute

from core.error_handling import AppError
from shared.logging.AppLogger import system_logger as syslog

SortableColumn = ColumnElement[object] | InstrumentedAttribute[object]

_SORTABLE_COLUMN_MAP: dict[str, SortableColumn] = {}


def add_sortable_column(field_name: str, column: SortableColumn) -> None:
    """Register a sortable field/key mapping."""
    _SORTABLE_COLUMN_MAP[field_name] = column


def resolve_sort(sort_by: str | None) -> tuple[ColumnElement[object], str]:
    """Resolve a sort expression ('-field') into a SQLAlchemy expression."""
    syslog.debug("resolve_sort", extra={"sort_by": sort_by})
    raw = sort_by or "-createdAt"
    descending = raw.startswith("-")
    key = raw.lstrip("+-")
    column = _SORTABLE_COLUMN_MAP.get(key)
    if column is None:
        syslog.error("unsupported sortBy", extra={"sort_by": raw})
        raise AppError(status_code=400, message=f"unsupported sortBy '{raw}'", code="invalid_input")
    expression = column.desc() if descending else column.asc()
    return expression, raw


__all__ = ["add_sortable_column", "resolve_sort"]

