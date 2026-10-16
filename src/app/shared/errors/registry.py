"""Central error code registry with German user-facing messages.

Every error code maps to an ErrorEntry with a user-friendly German message,
a toast type (error/warning/info), an HTTP status code, and an optional
developer-only hint (loesung).
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ErrorEntry:
    code: str
    message: str
    type: Literal["error", "warning", "info"] = "error"
    http_status: int = 400
    loesung: str | None = None


# ---------------------------------------------------------------------------
# Registry — keyed by error code
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, ErrorEntry] = {}


def _r(entry: ErrorEntry) -> ErrorEntry:
    _REGISTRY[entry.code] = entry
    return entry


# -- Auth -------------------------------------------------------------------
AUTH_INVALID_CREDENTIALS = _r(
    ErrorEntry(
        code="AUTH_INVALID_CREDENTIALS",
        message="Anmeldedaten sind ungültig. Bitte überprüfen Sie Ihre Eingaben.",
        http_status=401,
        loesung="E-Mail und Passwort prüfen.",
    )
)
AUTH_REQUIRED = _r(
    ErrorEntry(
        code="AUTH_REQUIRED",
        message="Bitte melden Sie sich an, um fortzufahren.",
        http_status=401,
        loesung="Gültigen API-Token bereitstellen.",
    )
)
AUTH_FORBIDDEN = _r(
    ErrorEntry(
        code="AUTH_FORBIDDEN",
        message="Sie haben keine Berechtigung für diese Aktion.",
        http_status=403,
        loesung="Rollen des Benutzers prüfen.",
    )
)

# -- Validation -------------------------------------------------------------
VALIDATION_REQUIRED_FIELD = _r(
    ErrorEntry(
        code="VALIDATION_REQUIRED_FIELD",
        message="Bitte füllen Sie alle Pflichtfelder aus.",
        type="warning",
        http_status=400,
        loesung="Fehlende Pflichtfelder ergänzen.",
    )
)
VALIDATION_INVALID_EMAIL = _r(
    ErrorEntry(
        code="VALIDATION_INVALID_EMAIL",
        message="Bitte geben Sie eine gültige E-Mail-Adresse ein.",
        type="warning",
        http_status=400,
    )
)
VALIDATION_LIMIT_RANGE = _r(
    ErrorEntry(
        code="VALIDATION_LIMIT_RANGE",
        message="Der angegebene Wert liegt außerhalb des erlaubten Bereichs.",
        type="warning",
        http_status=400,
        loesung="Wert muss zwischen 1 und 200 liegen.",
    )
)
VALIDATION_FAILED = _r(
    ErrorEntry(
        code="VALIDATION_FAILED",
        message="Die Eingabe konnte nicht verarbeitet werden. Bitte überprüfen Sie Ihre Daten.",
        type="warning",
        http_status=400,
    )
)
VALIDATION_INVALID_FORMAT = _r(
    ErrorEntry(
        code="VALIDATION_INVALID_FORMAT",
        message="Das Format der Eingabe ist ungültig.",
        type="warning",
        http_status=400,
    )
)
VALIDATION_INVALID_ENUM = _r(
    ErrorEntry(
        code="VALIDATION_INVALID_ENUM",
        message="Der angegebene Wert ist nicht zulässig.",
        type="warning",
        http_status=400,
    )
)
VALIDATION_INVALID_SORT = _r(
    ErrorEntry(
        code="VALIDATION_INVALID_SORT",
        message="Der Sortierparameter ist ungültig.",
        type="warning",
        http_status=400,
        loesung="Erlaubte Werte: createdAt, -createdAt.",
    )
)
VALIDATION_INVALID_PASSWORD = _r(
    ErrorEntry(
        code="VALIDATION_INVALID_PASSWORD",
        message="Das Passwort erfüllt die Sicherheitsanforderungen nicht.",
        type="warning",
        http_status=400,
    )
)
VALIDATION_INVALID_WATERMARK = _r(
    ErrorEntry(
        code="VALIDATION_INVALID_WATERMARK",
        message="Ungültige Wasserzeichen-Position.",
        type="warning",
        http_status=400,
    )
)

# -- File -------------------------------------------------------------------
FILE_TOO_LARGE = _r(
    ErrorEntry(
        code="FILE_TOO_LARGE",
        message="Die Datei ist zu groß. Bitte wählen Sie eine kleinere Datei.",
        type="warning",
        http_status=400,
    )
)
FILE_INVALID_TYPE = _r(
    ErrorEntry(
        code="FILE_INVALID_TYPE",
        message="Dieser Dateityp wird nicht unterstützt.",
        type="warning",
        http_status=400,
    )
)
FILE_NOT_FOUND = _r(
    ErrorEntry(
        code="FILE_NOT_FOUND",
        message="Die Datei wurde nicht gefunden.",
        http_status=404,
    )
)

# -- Job --------------------------------------------------------------------
JOB_NOT_FOUND = _r(
    ErrorEntry(
        code="JOB_NOT_FOUND",
        message="Der Auftrag wurde nicht gefunden.",
        http_status=404,
    )
)
JOB_EXPIRED = _r(
    ErrorEntry(
        code="JOB_EXPIRED",
        message="Der Auftrag ist abgelaufen. Bitte starten Sie einen neuen.",
        http_status=410,
    )
)
JOB_FAILED = _r(
    ErrorEntry(
        code="JOB_FAILED",
        message="Die Verarbeitung des Auftrags ist fehlgeschlagen.",
        http_status=500,
    )
)
JOB_ALREADY_COMPLETED = _r(
    ErrorEntry(
        code="JOB_ALREADY_COMPLETED",
        message="Der Auftrag wurde bereits abgeschlossen.",
        http_status=409,
    )
)

# -- Token ------------------------------------------------------------------
TOKEN_NOT_FOUND = _r(
    ErrorEntry(
        code="TOKEN_NOT_FOUND",
        message="Der Token wurde nicht gefunden.",
        http_status=404,
    )
)
TOKEN_EXPIRED = _r(
    ErrorEntry(
        code="TOKEN_EXPIRED",
        message="Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.",
        http_status=410,
    )
)

# -- Resource (generic) -----------------------------------------------------
RESOURCE_NOT_FOUND = _r(
    ErrorEntry(
        code="RESOURCE_NOT_FOUND",
        message="Die angeforderte Ressource wurde nicht gefunden.",
        http_status=404,
    )
)
RESOURCE_CONFLICT = _r(
    ErrorEntry(
        code="RESOURCE_CONFLICT",
        message="Die Ressource wurde zwischenzeitlich geändert. Bitte laden Sie die Seite neu.",
        http_status=409,
    )
)
RESOURCE_GONE = _r(
    ErrorEntry(
        code="RESOURCE_GONE",
        message="Die Ressource ist nicht mehr verfügbar.",
        http_status=410,
    )
)

# -- Server / External ------------------------------------------------------
SERVER_ERROR = _r(
    ErrorEntry(
        code="SERVER_ERROR",
        message="Es ist ein technisches Problem aufgetreten. Bitte versuchen Sie es später erneut.",
        http_status=500,
    )
)
EXTERNAL_SERVICE_ERROR = _r(
    ErrorEntry(
        code="EXTERNAL_SERVICE_ERROR",
        message="Ein externer Dienst ist derzeit nicht erreichbar. Bitte versuchen Sie es später erneut.",
        http_status=503,
    )
)
INVALID_REQUEST = _r(
    ErrorEntry(
        code="INVALID_REQUEST",
        message="Ungültige Anfrage. Bitte überprüfen Sie Ihre Eingaben.",
        type="warning",
        http_status=400,
    )
)
PAYLOAD_TOO_LARGE = _r(
    ErrorEntry(
        code="PAYLOAD_TOO_LARGE",
        message="Die Anfrage ist zu groß. Bitte reduzieren Sie die Datenmenge.",
        type="warning",
        http_status=413,
    )
)

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

_DEFAULT = ErrorEntry(
    code="UNKNOWN_ERROR",
    message="Ein unbekannter Fehler ist aufgetreten. Bitte versuchen Sie es erneut.",
    http_status=500,
)


def get_error(code: str) -> ErrorEntry | None:
    """Look up an error entry by code. Returns None if not found."""
    return _REGISTRY.get(code)


def get_error_or_default(code: str) -> ErrorEntry:
    """Look up an error entry by code; falls back to a generic error."""
    return _REGISTRY.get(code, _DEFAULT)


__all__ = [
    "ErrorEntry",
    "get_error",
    "get_error_or_default",
    # Module-level constants for convenient imports
    "AUTH_FORBIDDEN",
    "AUTH_INVALID_CREDENTIALS",
    "AUTH_REQUIRED",
    "EXTERNAL_SERVICE_ERROR",
    "FILE_INVALID_TYPE",
    "FILE_NOT_FOUND",
    "FILE_TOO_LARGE",
    "INVALID_REQUEST",
    "JOB_ALREADY_COMPLETED",
    "JOB_EXPIRED",
    "JOB_FAILED",
    "JOB_NOT_FOUND",
    "PAYLOAD_TOO_LARGE",
    "RESOURCE_CONFLICT",
    "RESOURCE_GONE",
    "RESOURCE_NOT_FOUND",
    "SERVER_ERROR",
    "TOKEN_EXPIRED",
    "TOKEN_NOT_FOUND",
    "VALIDATION_FAILED",
    "VALIDATION_INVALID_EMAIL",
    "VALIDATION_INVALID_ENUM",
    "VALIDATION_INVALID_FORMAT",
    "VALIDATION_INVALID_PASSWORD",
    "VALIDATION_INVALID_SORT",
    "VALIDATION_INVALID_WATERMARK",
    "VALIDATION_LIMIT_RANGE",
    "VALIDATION_REQUIRED_FIELD",
]
