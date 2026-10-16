import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.config import get_app_settings, get_db_settings
from app.core.core_api.healthcheck import healthcheck_router
from app.core.core_extensions.loader import (
    get_service_registrations,
    discover_service_module_names,
    register_service_routers,
    run_service_shutdown,
    run_service_startup,
)
from app.core.core_messages.middleware import register_message_language_middleware
from app.core.core_middleware.http_security_middleware import (
    SecurityHeadersConfig,
    register_http_logging_middleware,
    register_rate_limit_middleware,
    register_request_id_middleware,
    register_request_size_middleware,
    register_security_headers_middleware,
)
from app.core.startup_checks import perform_startup_checks
from app.shared.errors.handlers import install_unified_exception_handlers

logger = logging.getLogger("app_logger")


def join_path(prefix: str | None, suffix: str) -> str:
    """
    Joins API prefix + route suffix into a normalized absolute path.

    Examples:
        join_path("", "docs") -> "/docs"
        join_path("/api", "/docs") -> "/api/docs"
        join_path("api/", "openapi.json") -> "/api/openapi.json"
    """
    p = (prefix or "").strip("/")
    s = suffix.strip("/")
    return f"/{s}" if not p else f"/{p}/{s}"


def register_core_routers(app: FastAPI, api_prefix: str) -> None:
    app.include_router(healthcheck_router)
    app.include_router(healthcheck_router, prefix=api_prefix)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_settings = get_app_settings()
    db_settings = get_db_settings()

    logger.info("Starting app with LOG_LEVEL=%s", app_settings.LOG_LEVEL.value)

    if db_settings.DB_ENABLED:
        # Delegate all DB/S3 probes and migration orchestration to a single
        # function to keep this module focused on HTTP app wiring.
        await perform_startup_checks()
    else:
        logger.info("Database disabled - skipping DB init")

    # Startup: services
    service_regs = getattr(app.state, "service_registrations", [])
    runtime_services = await run_service_startup(app, service_regs)
    app.state.runtime_services = runtime_services

    try:
        yield
    finally:
        # Shutdown: services
        try:
            await run_service_shutdown(app, getattr(app.state, "runtime_services", []))
        except Exception:
            logger.exception("Service shutdown failed")

        logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app_settings = get_app_settings()

    app = FastAPI(
        lifespan=lifespan,
        docs_url=join_path(app_settings.API_PREFIX, "docs"),
        redoc_url=join_path(app_settings.API_PREFIX, "redoc"),
        openapi_url=join_path(app_settings.API_PREFIX, "openapi.json"),
    )

    # CORS
    origins = app_settings.cors_allowed_origins
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=app_settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=app_settings.cors_allow_methods,
            allow_headers=app_settings.cors_allow_headers,
        )

    # Middleware (registered in reverse call order — last registered runs first)
    register_message_language_middleware(app)
    register_request_id_middleware(app)
    register_http_logging_middleware(
        app,
        enabled=app_settings.HTTP_LOGGING_ENABLED,
        request_logging_enabled=app_settings.HTTP_REQUEST_LOGGING_ENABLED,
        response_logging_enabled=app_settings.HTTP_RESPONSE_LOGGING_ENABLED,
        fault_logging_enabled=app_settings.HTTP_FAULT_LOGGING_ENABLED,
    )
    register_request_size_middleware(
        app,
        max_request_size_bytes=app_settings.MAX_REQUEST_SIZE_BYTES,
        max_upload_size_bytes=app_settings.MAX_UPLOAD_SIZE_BYTES,
    )
    register_security_headers_middleware(
        app,
        SecurityHeadersConfig(
            enabled=app_settings.SECURITY_HEADERS_ENABLED,
            hsts_enabled=app_settings.SECURITY_HEADERS_HSTS_ENABLED,
            hsts_max_age=app_settings.SECURITY_HEADERS_HSTS_MAX_AGE,
            csp_enabled=app_settings.SECURITY_HEADERS_CSP_ENABLED,
            csp_directives=app_settings.SECURITY_HEADERS_CSP_DIRECTIVES,
            x_frame_options=app_settings.SECURITY_HEADERS_X_FRAME_OPTIONS,
        ),
    )
    register_rate_limit_middleware(
        app,
        enabled=app_settings.RATE_LIMIT_ENABLED,
        max_requests=app_settings.RATE_LIMIT_MAX_REQUESTS,
        window_seconds=app_settings.RATE_LIMIT_WINDOW_SECONDS,
    )

    # Global error handlers (unified error envelope for all services)
    install_unified_exception_handlers(app)

    # Routers
    register_core_routers(app, app_settings.API_PREFIX)

    module_names = discover_service_module_names()
    if module_names:
        service_registrations = get_service_registrations()
    else:
        service_registrations = []

    register_service_routers(app, app_settings.API_PREFIX, service_registrations)
    app.state.service_registrations = service_registrations

    return app


app = create_app()
