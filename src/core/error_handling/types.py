from __future__ import annotations

"""Typed error primitives."""

from dataclasses import dataclass
from typing import Literal

ErrorType = Literal[
    "validation_error",
    "invalid_input",
    "conflict",
    "database_error",
    "internal_error",
    "app_error",
    "not_found",
    "http_error",
    "unauthorized",
    "forbidden",
]


@dataclass(slots=True)
class AppError(Exception):
    """Domain-level application error translated by exception handlers."""

    status_code: int
    message: str
    code: ErrorType | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial repr
        return f"{self.status_code} {self.code or ''} {self.message}"


__all__ = ["AppError", "ErrorType"]
