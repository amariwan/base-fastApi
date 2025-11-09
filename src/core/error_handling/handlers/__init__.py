from __future__ import annotations

"""Aggregate registration for FastAPI exception handlers."""

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.error_handling.types import AppError
from core.errors import ConflictError, NotFoundError, ValidationError

from .database_handlers import handle_integrity_error, handle_sqlalchemy_error
from .domain_handlers import (
    handle_domain_conflict,
    handle_domain_not_found,
    handle_domain_validation,
)
from .http_handlers import handle_http_exception, handle_request_validation_error
from .system_handlers import handle_app_error, handle_unhandled


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    handlers = {
        HTTPException: handle_http_exception,
        RequestValidationError: handle_request_validation_error,
        IntegrityError: handle_integrity_error,
        SQLAlchemyError: handle_sqlalchemy_error,
        AppError: handle_app_error,
        ValidationError: handle_domain_validation,
        ConflictError: handle_domain_conflict,
        NotFoundError: handle_domain_not_found,
        Exception: handle_unhandled,
    }
    for exception_type, handler in handlers.items():
        app.add_exception_handler(exception_type, handler)


__all__ = ["register_exception_handlers"]

