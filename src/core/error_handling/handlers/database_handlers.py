from __future__ import annotations

"""Database error handlers."""

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from shared.logging.AppLogger import system_logger as syslog
from shared.logging.request_context import get_request_id

from ..payload import json_error


async def handle_integrity_error(request: Request, exc: IntegrityError) -> Response:
    """Translate IntegrityError to 409."""
    rid = get_request_id()
    syslog.warning("db_integrity_error", extra={"path": str(request.url), "rid": rid})
    return json_error(
        status=HTTPStatus.CONFLICT,
        kind="conflict",
        message="Conflict",
        details={"Database": ["Constraint violation"]},
        request_id=rid,
    )


async def handle_sqlalchemy_error(request: Request, exc: SQLAlchemyError) -> Response:
    """Translate unexpected SQLAlchemy errors to 500."""
    rid = get_request_id()
    syslog.error("db_error", extra={"path": str(request.url), "rid": rid})
    return json_error(
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        kind="database_error",
        message="Internal Server Error",
        details={"Database": ["Internal database error"]},
        request_id=rid,
    )


__all__ = ["handle_integrity_error", "handle_sqlalchemy_error"]

