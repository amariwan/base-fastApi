"""Common error schema models used across services.

The unified error envelope shape:
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

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorFieldDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    reason: str
    expected: str | None = None


class ErrorPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str
    message: str
    type: Literal["error", "warning", "info"] = "error"
    traceId: str
    timestamp: str
    details: list[ErrorFieldDetail] | None = None
    dev: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorPayload


class ErrorResponse(BaseModel):
    """Standard error response for API endpoints."""

    detail: str = Field(..., description="Error message")
    code: str | None = Field(None, description="Error code")


__all__ = [
    "ErrorEnvelope",
    "ErrorFieldDetail",
    "ErrorPayload",
    "ErrorResponse",
]
