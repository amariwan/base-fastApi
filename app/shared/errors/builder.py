"""Build unified error response envelopes.

Every error response follows the shape:
  {
    "error": {
      "code": "ERROR_CODE",
      "message": "German user-facing message",
      "type": "error" | "warning" | "info",
      "traceId": "hex-uuid",
      "timestamp": "ISO-8601 UTC",
      "details": [...] | null,
      "dev": {...} | null
    }
  }
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from .registry import get_error_or_default


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def build_error_response(
    code: str,
    *,
    message: str | None = None,
    type: Literal["error", "warning", "info"] | None = None,
    details: list[dict[str, Any]] | None = None,
    dev: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a unified error envelope.

    Looks up *code* in the registry for defaults; explicit kwargs override.

    Args:
        code: Machine-readable error code (e.g. "TEMPLATE_NOT_FOUND").
        message: Override the registry's German message.
        type: Override the toast type ("error", "warning", "info").
        details: Optional list of field-level error details.
        dev: Optional developer-only information (loesung, exception type, etc.).

    Returns:
        Dict ready to be serialized as JSON response body.
    """
    entry = get_error_or_default(code)

    payload: dict[str, Any] = {
        "code": code,
        "message": message if message is not None else entry.message,
        "type": type if type is not None else entry.type,
        "traceId": uuid4().hex,
        "timestamp": _utc_now(),
    }

    if details:
        payload["details"] = details
    if dev:
        payload["dev"] = dev

    return {"error": payload}


__all__ = ["build_error_response"]
