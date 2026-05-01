"""API error models with standardized HTTP status codes and messages.

All errors now produce the unified error envelope:
  {
    "error": {
      "code": "ERROR_CODE",
      "message": "German-language error message",
      "type": "error" | "warning" | "info",
      "traceId": "...",
      "timestamp": "...",
      "dev": {"loesung": "..."}
    }
  }

Services can subclass ApiError or use these base types.
"""

from app.shared.errors.exceptions import UnifiedApiError


class ApiError(UnifiedApiError):
    """Base API error with standard error response format.

    Now a subclass of UnifiedApiError. Keeps the same constructor
    signature for backwards compatibility.

    Attributes:
        code: Machine-readable error code (e.g., "VALIDATION_FAILED")
        message: German-language description
        loesung: German-language solution or suggested action
        http_status: HTTP status code (default 400)
    """

    def __init__(
        self,
        code: str,
        message: str,
        loesung: str,
        http_status: int = 400,
    ):
        self.loesung = loesung
        super().__init__(
            code,
            message=message,
            http_status=http_status,
            dev={"loesung": loesung} if loesung else None,
        )

    def to_dict(self) -> dict:
        """Convert to API response dict (legacy format for backwards compat)."""
        return {
            "detail": {
                "code": self.code,
                "message": self.message,
                "loesung": self.loesung,
            }
        }


class NotFoundError(ApiError):
    """404 Not Found - resource does not exist."""

    def __init__(
        self,
        code: str = "NOT_FOUND",
        message: str = "Ressource nicht gefunden",
        loesung: str = "Überprüfen Sie die ID oder erstellen Sie die Ressource neu",
    ):
        super().__init__(code, message, loesung, http_status=404)


class UnauthorizedError(ApiError):
    """401 Unauthorized - authentication required."""

    def __init__(
        self,
        code: str = "UNAUTHORIZED",
        message: str = "Authentifizierung erforderlich",
        loesung: str = "Stellen Sie einen gültigen API-Token bereit",
    ):
        super().__init__(code, message, loesung, http_status=401)


class BadRequestError(ApiError):
    """400 Bad Request - invalid input."""

    def __init__(
        self,
        code: str = "BAD_REQUEST",
        message: str = "Ungültige Eingabe",
        loesung: str = "Überprüfen Sie die Request-Parameter",
    ):
        super().__init__(code, message, loesung, http_status=400)


class ConflictError(ApiError):
    """409 Conflict - state conflict (e.g., already exists)."""

    def __init__(
        self,
        code: str = "CONFLICT",
        message: str = "Konflikt",
        loesung: str = "Überprüfen Sie den aktuellen Zustand und versuchen Sie es erneut",
    ):
        super().__init__(code, message, loesung, http_status=409)


class GoneError(ApiError):
    """410 Gone - resource expired or permanently deleted."""

    def __init__(
        self,
        code: str = "GONE",
        message: str = "Ressource nicht mehr verfügbar",
        loesung: str = "Fordern Sie eine neue Ressource an",
    ):
        super().__init__(code, message, loesung, http_status=410)


class ExternalApiError(ApiError):
    """503 Service Unavailable - external service error."""

    def __init__(
        self,
        code: str = "EXTERNAL_API_ERROR",
        message: str = "Externer Service nicht verfügbar",
        loesung: str = "Versuchen Sie es später erneut",
    ):
        super().__init__(code, message, loesung, http_status=503)
