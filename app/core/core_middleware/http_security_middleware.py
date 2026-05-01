from __future__ import annotations

import logging
import time
import uuid
from asyncio import Lock
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.core.core_messages import MessageKeys, msg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

logger = logging.getLogger("app_logger")


@dataclass(frozen=True)
class SecurityHeadersConfig:
    enabled: bool
    hsts_enabled: bool
    hsts_max_age: int
    csp_enabled: bool
    csp_directives: str
    x_frame_options: str | None = None


def register_http_logging_middleware(
    app: FastAPI,
    *,
    enabled: bool,
    request_logging_enabled: bool,
    response_logging_enabled: bool,
    fault_logging_enabled: bool,
) -> None:
    if not enabled:
        return

    @app.middleware("http")
    async def http_logging_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.time()
        if request_logging_enabled:
            logger.info(
                "HTTP request %s %s from %s",
                request.method,
                request.url.path,
                request.client.host if request.client else "unknown",
            )

        try:
            response = await call_next(request)
        except Exception:
            if fault_logging_enabled:
                logger.exception("HTTP failure %s %s", request.method, request.url.path)
            raise

        if response_logging_enabled:
            duration_ms = int((time.time() - started) * 1000)
            logger.info(
                "HTTP response %s %s -> %s in %sms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
        return response


def register_api_key_middleware(app: FastAPI, *, enabled: bool, header_name: str, expected_api_key: str | None) -> None:
    if not enabled:
        return

    if not expected_api_key:
        logger.warning(msg.get(MessageKeys.API_KEY_PROTECTION_ENABLED_BUT_EMPTY))

    @app.middleware("http")
    async def api_key_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if not expected_api_key:
            return JSONResponse(
                status_code=500,
                content={"detail": msg.get(MessageKeys.API_KEY_NOT_CONFIGURED)},
            )
        if request.headers.get(header_name) != expected_api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": msg.get(MessageKeys.API_KEY_INVALID_OR_MISSING)},
            )
        return await call_next(request)


def register_request_size_middleware(app: FastAPI, *, max_request_size_bytes: int, max_upload_size_bytes: int) -> None:
    @app.middleware("http")
    async def request_size_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                size = 0

            is_upload = request.headers.get("content-type", "").startswith("multipart/form-data")
            limit = max_upload_size_bytes if is_upload else max_request_size_bytes
            if size > limit:
                return JSONResponse(
                    status_code=413,
                    content={"detail": msg.get(MessageKeys.REQUEST_TOO_LARGE, limit=limit)},
                )
        return await call_next(request)


def register_security_headers_middleware(
    app: FastAPI,
    config: SecurityHeadersConfig,
) -> None:
    if not config.enabled:
        return

    @app.middleware("http")
    async def security_headers_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if config.x_frame_options:
            response.headers.setdefault("X-Frame-Options", config.x_frame_options)
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if config.hsts_enabled:
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={config.hsts_max_age}; includeSubDomains",
            )
        if config.csp_enabled and config.csp_directives:
            response.headers.setdefault("Content-Security-Policy", config.csp_directives)
        return response


def register_request_id_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def register_rate_limit_middleware(app: FastAPI, *, enabled: bool, max_requests: int, window_seconds: int) -> None:
    if not enabled:
        return

    windows: dict[str, list[float]] = defaultdict(list)
    lock = Lock()
    # Track request count for periodic cleanup without unbounded memory growth
    req_count: list[int] = [0]
    cleanup_interval = 500

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        client_id = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - window_seconds

        async with lock:
            hits = [t for t in windows[client_id] if t >= cutoff]
            if len(hits) >= max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": msg.get(MessageKeys.RATE_LIMIT_EXCEEDED)},
                    headers={
                        "Retry-After": str(window_seconds),
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(min(hits) + window_seconds)),
                    },
                )
            hits.append(now)
            windows[client_id] = hits

            # Periodically remove entries for clients whose window has fully expired
            req_count[0] += 1
            if req_count[0] >= cleanup_interval:
                req_count[0] = 0
                stale = [k for k, ts in windows.items() if not any(t >= cutoff for t in ts)]
                for k in stale:
                    del windows[k]

        return await call_next(request)
