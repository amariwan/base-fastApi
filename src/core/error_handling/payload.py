from __future__ import annotations

"""RFC 7807 problem+json helpers."""

from http import HTTPStatus
from typing import TypedDict

from fastapi.responses import JSONResponse

from shared.types import JSONValue

from .types import ErrorType

MEDIA_TYPE = "application/problem+json"


class ProblemDetails(TypedDict, total=False):
    type: str
    title: str
    status: int
    errors: dict[str, list[str]]
    traceId: str


_TYPE_MAP = {
    HTTPStatus.BAD_REQUEST: "https://www.rfc-editor.org/rfc/rfc9110.html#name-400-bad-request",
    HTTPStatus.UNAUTHORIZED: "https://www.rfc-editor.org/rfc/rfc9110.html#name-401-unauthorized",
    HTTPStatus.FORBIDDEN: "https://www.rfc-editor.org/rfc/rfc9110.html#name-403-forbidden",
    HTTPStatus.NOT_FOUND: "https://www.rfc-editor.org/rfc/rfc9110.html#name-404-not-found",
    HTTPStatus.CONFLICT: "https://www.rfc-editor.org/rfc/rfc9110.html#name-409-conflict",
    HTTPStatus.UNPROCESSABLE_ENTITY: "https://www.rfc-editor.org/rfc/rfc9110.html#name-422-unprocessable-content",
    HTTPStatus.INTERNAL_SERVER_ERROR: "https://www.rfc-editor.org/rfc/rfc9110.html#name-500-internal-server-error",
}


def _to_errors(details: JSONValue) -> dict[str, list[str]] | None:
    if details is None:
        return None
    if isinstance(details, list):
        output: dict[str, list[str]] = {}
        for item in details:
            if not isinstance(item, dict):
                continue
            loc = item.get("loc", ["unknown"])
            field = str(loc[-1]) if isinstance(loc, list) and loc else "unknown"
            msg = str(item.get("msg", "validation error"))
            output.setdefault(field, []).append(msg)
        return output or None
    if isinstance(details, dict):
        normalized: dict[str, list[str]] = {}
        for key, value in details.items():
            if isinstance(value, list):
                normalized[str(key)] = [str(v) for v in value]
            else:
                normalized[str(key)] = [str(value)]
        return normalized
    return {"_errors": [str(details)]}


def build_problem(
    *,
    status: int,
    title: str,
    errors: dict[str, list[str]] | None,
    trace_id: str | None,
) -> ProblemDetails:
    """Build a ProblemDetails payload honoring RFC links."""
    http_status = HTTPStatus(status)
    problem: ProblemDetails = {
        "type": _TYPE_MAP.get(http_status, f"https://www.rfc-editor.org/rfc/rfc9110.html#name-{http_status.value}"),
        "title": title,
        "status": http_status.value,
    }
    if errors:
        problem["errors"] = errors
    if trace_id:
        problem["traceId"] = trace_id
    return problem


def json_error(
    *,
    status: int | HTTPStatus,
    kind: ErrorType,
    message: str | None,
    details: JSONValue,
    request_id: str | None,
) -> JSONResponse:
    """Return a JSONResponse with RFC 7807 content."""
    http_status = HTTPStatus(status)
    title = message or http_status.phrase
    return JSONResponse(
        status_code=http_status.value,
        media_type=MEDIA_TYPE,
        content=build_problem(
            status=http_status.value,
            title=title,
            errors=_to_errors(details),
            trace_id=request_id,
        ),
    )


__all__ = ["ProblemDetails", "json_error", "build_problem", "MEDIA_TYPE"]

