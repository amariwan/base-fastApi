from __future__ import annotations

"""Domain error types used across the application.

This module provides simple, serializable exception types that represent
domain-level errors (validation, conflict, not-found). Handlers expect an
`.message` attribute on these exceptions.
"""

from dataclasses import dataclass


@dataclass
class DomainError(Exception):
    """Base class for domain errors carrying a message."""

    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class ValidationError(DomainError):
    """Represents a domain validation error."""


class ConflictError(DomainError):
    """Represents a domain conflict error (e.g. unique constraint semantics)."""


class NotFoundError(DomainError):
    """Represents a domain not-found error."""


__all__ = ["DomainError", "ValidationError", "ConflictError", "NotFoundError"]
