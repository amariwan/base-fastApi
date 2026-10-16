"""Shared schema definitions used across services."""

from .errors import ErrorEnvelope, ErrorFieldDetail, ErrorPayload, ErrorResponse

__all__ = [
    "ErrorEnvelope",
    "ErrorFieldDetail",
    "ErrorPayload",
    "ErrorResponse",
]
