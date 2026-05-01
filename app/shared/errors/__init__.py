"""Unified error handling for all services.

Provides a centralized error registry, exception base class, and response builder.
All user-facing error messages are in German.
"""

from .builder import build_error_response
from .exceptions import UnifiedApiError
from .registry import ErrorEntry, get_error, get_error_or_default

__all__ = [
    "ErrorEntry",
    "UnifiedApiError",
    "build_error_response",
    "get_error",
    "get_error_or_default",
]
