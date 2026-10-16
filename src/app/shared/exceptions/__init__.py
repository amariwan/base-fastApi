"""Shared API error handling and response models.

This module centralizes error handling across services, providing:
  - ApiError: base exception with error code, message, and solution
  - HTTP exception mapping for standard status codes
"""

from .api_errors import (
    ApiError,
    BadRequestError,
    ConflictError,
    ExternalApiError,
    GoneError,
    NotFoundError,
    UnauthorizedError,
)

__all__ = [
    "ApiError",
    "NotFoundError",
    "UnauthorizedError",
    "BadRequestError",
    "ConflictError",
    "GoneError",
    "ExternalApiError",
]
