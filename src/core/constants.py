from __future__ import annotations

"""Core-wide constants to avoid scattering magic strings."""

from typing import Final

# Routing / API
API_PREFIX_ENV: Final[str] = "API_PREFIX"
API_VERSION_ENV: Final[str] = "API_VERSION"
DEFAULT_API_PREFIX: Final[str] = "/api"
DEFAULT_API_VERSION: Final[str] = "v1"

# Logging / tracing
REQUEST_ID_HEADER: Final[str] = "X-Request-ID"

# Security headers
DEFAULT_REFERRER_POLICY: Final[str] = "no-referrer"
DEFAULT_PERMISSIONS_POLICY: Final[str] = "geolocation=(), microphone=(), camera=()"

# CORS defaults
DEFAULT_CORS_ALLOW_HEADERS: Final[tuple[str, ...]] = ("Authorization", "Content-Type")
DEFAULT_CORS_ALLOW_METHODS: Final[tuple[str, ...]] = (
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "OPTIONS",
)

__all__ = [
    "API_PREFIX_ENV",
    "API_VERSION_ENV",
    "DEFAULT_API_PREFIX",
    "DEFAULT_API_VERSION",
    "REQUEST_ID_HEADER",
    "DEFAULT_REFERRER_POLICY",
    "DEFAULT_PERMISSIONS_POLICY",
    "DEFAULT_CORS_ALLOW_HEADERS",
    "DEFAULT_CORS_ALLOW_METHODS",
]

