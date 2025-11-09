from __future__ import annotations

"""System level error handlers."""

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import Response

from shared.logging.AppLogger import system_logger as syslog
from shared.logging.request_context import get_request_id

from ..payload import json_error
from ..types import AppError


async def handle_app_error(request: Request, exc: AppError) -> Response:
    """Translate AppError instances to RFC payloads."""
    rid = get_request_id()
    syslog.warning(
        "app_error", extra={"path": str(request.url), "code": exc.code, "rid": rid}
    )
    return json_error(
        status=exc.status_code,
        kind=exc.code or "app_error",
        message="Application Error",
        details={exc.code or "error": [exc.message]},
        request_id=rid,
    )


async def handle_unhandled(request: Request, exc: Exception) -> Response:
    """Catch-all handler for unexpected exceptions."""
    rid = get_request_id()
    syslog.exception("unhandled_exception", extra={"path": str(request.url), "rid": rid})
    return json_error(
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        kind="internal_error",
        message="Internal Server Error",
        details={"Error": ["Internal error"]},
        request_id=rid,
    )


__all__ = ["handle_app_error", "handle_unhandled"]

