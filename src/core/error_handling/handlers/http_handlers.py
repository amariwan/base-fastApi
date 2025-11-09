from __future__ import annotations

"""HTTP and validation exception handlers."""

from http import HTTPStatus

from fastapi import Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import Response

from shared.logging.AppLogger import system_logger as syslog
from shared.logging.request_context import get_request_id

from ..payload import json_error

_STATUS_TITLE = {
    HTTPStatus.BAD_REQUEST: "Bad Request",
    HTTPStatus.UNAUTHORIZED: "Unauthorized",
    HTTPStatus.FORBIDDEN: "Forbidden",
    HTTPStatus.NOT_FOUND: "Not Found",
    HTTPStatus.UNPROCESSABLE_ENTITY: "Unprocessable Entity",
}


async def handle_http_exception(request: Request, exc: HTTPException) -> Response:
    """Format HTTPException responses as RFC 7807 payloads."""
    rid = get_request_id()
    syslog.warning(
        "http_exception",
        extra={"path": str(request.url), "status": exc.status_code, "rid": rid},
    )
    details = {"detail": [exc.detail]} if isinstance(exc.detail, str) else exc.detail
    status_code = HTTPStatus(exc.status_code)
    return json_error(
        status=status_code,
        kind="http_error",
        message=_STATUS_TITLE.get(status_code, "Error"),
        details=details,
        request_id=rid,
    )


async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> Response:
    """Format FastAPI validation errors as RFC 7807 payloads."""
    rid = get_request_id()
    syslog.warning("validation_error", extra={"path": str(request.url), "rid": rid})
    return json_error(
        status=HTTPStatus.UNPROCESSABLE_ENTITY,
        kind="validation_error",
        message=_STATUS_TITLE[HTTPStatus.UNPROCESSABLE_ENTITY],
        details=exc.errors(),
        request_id=rid,
    )


__all__ = ["handle_http_exception", "handle_request_validation_error"]

