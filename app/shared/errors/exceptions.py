"""Unified API exception that all services can raise.

UnifiedApiError resolves its fields from the error registry at construction
time, but allows per-instance overrides for message, type, details, etc.
A single global FastAPI exception handler catches it and returns the
standardized error envelope.
"""

from typing import Any, Literal

from .registry import get_error_or_default


class UnifiedApiError(Exception):
    """Base exception for all API errors across services.

    Resolves defaults from the error registry; explicit kwargs override.

    Attributes:
        code: Machine-readable error code.
        message: German user-facing message.
        error_type: Toast type sent to the frontend.
        http_status: HTTP status code for the response.
        details: Optional field-level validation details.
        dev: Optional developer-only information.
    """

    def __init__(  # noqa: PLR0913
        self,
        code: str,
        *,
        message: str | None = None,
        type: Literal["error", "warning", "info"] | None = None,
        http_status: int | None = None,
        details: list[dict[str, Any]] | None = None,
        dev: dict[str, Any] | None = None,
    ) -> None:
        entry = get_error_or_default(code)

        self.code: str = code
        self.message: str = message if message is not None else entry.message
        self.error_type: Literal["error", "warning", "info"] = type if type is not None else entry.type
        self.http_status: int = http_status if http_status is not None else entry.http_status
        self.details: list[dict[str, Any]] | None = details
        self.dev: dict[str, Any] | None = dev

        super().__init__(self.message)


__all__ = ["UnifiedApiError"]
