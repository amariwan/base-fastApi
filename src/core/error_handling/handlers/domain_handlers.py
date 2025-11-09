from __future__ import annotations

"""Handlers translating domain errors to ProblemDetails."""

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import Response

from core.errors import ConflictError, NotFoundError
from core.errors import ValidationError as DomainValidationError
from shared.logging.AppLogger import system_logger as syslog
from shared.logging.request_context import get_request_id

from ..payload import json_error


async def handle_domain_validation(
    request: Request, exc: DomainValidationError
) -> Response:
    """Return RFC payload for domain validation failures."""
    rid = get_request_id()
    syslog.warning("domain_validation", extra={"path": str(request.url), "rid": rid})
    return json_error(
        status=HTTPStatus.BAD_REQUEST,
        kind="validation_error",
        message="Bad Request",
        details={"Validation": [exc.message]},
        request_id=rid,
    )


async def handle_domain_conflict(request: Request, exc: ConflictError) -> Response:
    """Return RFC payload for domain conflict errors."""
    rid = get_request_id()
    syslog.warning("domain_conflict", extra={"path": str(request.url), "rid": rid})
    return json_error(
        status=HTTPStatus.CONFLICT,
        kind="conflict",
        message="Conflict",
        details={"Conflict": [exc.message]},
        request_id=rid,
    )


async def handle_domain_not_found(request: Request, exc: NotFoundError) -> Response:
    """Return RFC payload for missing resources."""
    rid = get_request_id()
    syslog.warning("domain_not_found", extra={"path": str(request.url), "rid": rid})
    return json_error(
        status=HTTPStatus.NOT_FOUND,
        kind="not_found",
        message="Not Found",
        details={"NotFound": [exc.message]},
        request_id=rid,
    )


__all__ = [
    "handle_domain_validation",
    "handle_domain_conflict",
    "handle_domain_not_found",
]

