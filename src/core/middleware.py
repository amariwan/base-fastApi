from __future__ import annotations

"""Centralized middleware registration with security defaults."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.responses import Response

from core.constants import (
    DEFAULT_CORS_ALLOW_HEADERS,
    DEFAULT_CORS_ALLOW_METHODS,
    DEFAULT_PERMISSIONS_POLICY,
    DEFAULT_REFERRER_POLICY,
    REQUEST_ID_HEADER,
)
from shared.logging.request_context import reset_request_id, set_request_id
from utils.env_helpers import first_env, read_env_bool, read_env_csv


def _csv_from_env(*names: str, default: tuple[str, ...]) -> list[str]:
    for name in names:
        values = read_env_csv(name)
        if values:
            return values
    return list(default)


def _add_request_id_middleware(app: FastAPI) -> None:
    trust_header = read_env_bool("TRUST_X_REQUEST_ID")

    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        header_value = request.headers.get(REQUEST_ID_HEADER)
        request_id = header_value if (trust_header and header_value) else str(uuid.uuid4())
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
            response.headers.setdefault(REQUEST_ID_HEADER, request_id)
            return response
        finally:
            reset_request_id(token)


def _add_gzip_middleware(app: FastAPI) -> None:
    app.add_middleware(GZipMiddleware, minimum_size=1024)


def _add_cors_middleware(app: FastAPI) -> None:
    origins = _csv_from_env("CORS_ALLOW_ORIGINS", "CORS_ALLOWED_ORIGINS", default=())
    headers = _csv_from_env(
        "CORS_ALLOW_HEADERS",
        "CORS_ALLOWED_HEADERS",
        default=DEFAULT_CORS_ALLOW_HEADERS,
    )
    methods = _csv_from_env(
        "CORS_ALLOW_METHODS",
        "CORS_ALLOWED_METHODS",
        default=DEFAULT_CORS_ALLOW_METHODS,
    )
    allow_credentials = read_env_bool("CORS_ALLOW_CREDENTIALS", default=True)
    max_age = int(first_env("CORS_MAX_AGE", default="600") or "600")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=methods,
        allow_headers=headers,
        max_age=max_age,
    )


def _security_headers_enabled() -> bool:
    return read_env_bool("SECURITY_HEADERS_ENABLE", default=True)


def _hsts_header() -> str | None:
    if not read_env_bool("HSTS_ENABLE", default=True):
        return None
    max_age = int(first_env("HSTS_MAX_AGE", default="63072000") or "63072000")
    return f"max-age={max_age}; includeSubDomains; preload"


def _add_security_headers_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if not _security_headers_enabled():
            return response

        hsts = _hsts_header()
        if hsts:
            response.headers.setdefault("Strict-Transport-Security", hsts)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if read_env_bool("XFRAME_DENY", default=True):
            response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy",
            first_env("REFERRER_POLICY", default=DEFAULT_REFERRER_POLICY) or DEFAULT_REFERRER_POLICY,
        )
        response.headers.setdefault("Permissions-Policy", DEFAULT_PERMISSIONS_POLICY)
        return response


def register_middleware(app: FastAPI) -> None:
    """Register all middlewares with secure defaults."""
    _add_request_id_middleware(app)
    _add_gzip_middleware(app)
    _add_cors_middleware(app)
    _add_security_headers_middleware(app)
