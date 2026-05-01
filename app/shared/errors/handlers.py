"""Global FastAPI exception handlers for unified error responses."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .builder import build_error_response
from .exceptions import UnifiedApiError


async def unified_api_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handle UnifiedApiError and return a standardized error envelope."""
    if not isinstance(exc, UnifiedApiError):
        body = build_error_response("SERVER_ERROR")
        return JSONResponse(status_code=500, content=body)

    body = build_error_response(
        exc.code,
        message=exc.message,
        type=exc.error_type,
        details=exc.details,
        dev=exc.dev,
    )
    return JSONResponse(status_code=exc.http_status, content=body)


async def unified_validation_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic RequestValidationError with the unified format."""
    if not isinstance(exc, RequestValidationError):
        body = build_error_response("SERVER_ERROR")
        return JSONResponse(status_code=500, content=body)

    details: list[dict[str, Any]] = []
    for issue in exc.errors():
        location = issue.get("loc", ())
        field = ".".join(str(part) for part in location if part != "body")
        details.append(
            {
                "field": field or "request",
                "reason": str(issue.get("type", "validation_error")),
                "expected": str(issue.get("msg", "invalid value")),
            }
        )

    body = build_error_response("VALIDATION_FAILED", details=details)
    return JSONResponse(status_code=400, content=body)


def install_unified_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    marker = "_unified_handlers_installed"
    if getattr(app.state, marker, False):
        return

    app.add_exception_handler(UnifiedApiError, unified_api_error_handler)
    app.add_exception_handler(RequestValidationError, unified_validation_error_handler)
    setattr(app.state, marker, True)


__all__ = [
    "install_unified_exception_handlers",
    "unified_api_error_handler",
    "unified_validation_error_handler",
]
