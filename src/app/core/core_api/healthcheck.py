import asyncio
import logging
from collections.abc import Mapping
from typing import Protocol, cast

from app.config import get_app_settings, get_db_settings
from app.core.core_auth.settings import get_auth_settings
from app.core.core_extensions.loader import RuntimeService, ServiceRegistration
from app.core.core_storage.settings import StorageBackend, get_storage_settings
from app.core.startup_checks import check_db
from app.core.startup_checks import check_s3 as check_storage
from app.shared.jobs.providers import get_arq_pool
from fastapi import APIRouter, Request, Response

from .health_diagnostics import health_status, make_health_result, service_startup_states
from .schemas import (
    HealthCheckResult,
    HealthConfig,
    HealthLiveResponse,
    HealthResponse,
    HealthSettingsApp,
    HealthSettingsDB,
    HealthStatus,
)

logger = logging.getLogger("app_logger")


class _Pingable(Protocol):
    async def ping(self) -> object: ...


router = APIRouter(tags=["health"])
healthcheck_router = router


def _collect_runtime_services(request: Request) -> dict[str, RuntimeService]:
    runtime_services = getattr(request.app.state, "runtime_services", [])
    return {runtime_service.registration.name: runtime_service for runtime_service in runtime_services}


def _serialize_health_config() -> HealthConfig | None:
    db_settings = get_db_settings()
    if not db_settings.DB_ENABLED:
        return None

    app_settings = get_app_settings()
    app_config = HealthSettingsApp.model_validate(
        {"LOG_LEVEL": app_settings.LOG_LEVEL.value, "TEST_MODE": app_settings.TEST_MODE}
    )
    db_config = HealthSettingsDB.model_validate(
        {
            "DB_BACKEND": db_settings.DB_BACKEND,
            "DB_PORT": db_settings.DB_PORT,
            "DB_DATABASE": cast(str, db_settings.DB_DATABASE),
        }
    )
    return HealthConfig.model_validate({"APP_SETTINGS": app_config, "DB_SETTINGS": db_config})


def _check_app_state(request: Request) -> HealthCheckResult:
    app_settings = get_app_settings()
    db_settings = get_db_settings()
    storage_settings = get_storage_settings()
    service_registrations = getattr(request.app.state, "service_registrations", [])
    runtime_services = getattr(request.app.state, "runtime_services", [])
    details: dict[str, object] = {
        "api_prefix": app_settings.API_PREFIX,
        "db_enabled": db_settings.DB_ENABLED,
        "log_level": app_settings.LOG_LEVEL.value,
        "runtime_services": len(runtime_services),
        "service_registrations": len(service_registrations),
        "storage_backend": storage_settings.STORAGE_BACKEND.value,
        "test_mode": app_settings.TEST_MODE,
    }
    message = "application settings loaded"
    try:
        auth_settings = get_auth_settings()
    except RuntimeError as exc:
        # get_auth_settings rejects insecure non-test configs by raising.
        # Health must never 500 on configuration alone; surface the issue instead.
        logger.warning("auth settings degraded: %s", exc)
        details["auth_mode"] = "unavailable"
        message = "application settings loaded (auth degraded)"
    else:
        details["auth_mode"] = auth_settings.MODE
    return make_health_result(
        "ok",
        message,
        details=details,
    )


def _collect_liveness_checks(request: Request) -> dict[str, HealthCheckResult]:
    return {"app": _check_app_state(request)}


async def _check_database() -> HealthCheckResult:
    db_settings = get_db_settings()
    if not db_settings.DB_ENABLED:
        return make_health_result("skipped", "database disabled", details={"enabled": False})

    app_settings = get_app_settings()
    ok, message = await check_db(timeout_seconds=app_settings.DB_PROBE_TIMEOUT_SECONDS)
    return make_health_result(
        "ok" if ok else "fail",
        "database probe ok" if ok else f"database probe failed: {message}",
        details={
            "backend": db_settings.DB_BACKEND,
            "database": cast(str, db_settings.DB_DATABASE),
            "enabled": True,
            "port": db_settings.DB_PORT,
            "timeout_seconds": app_settings.DB_PROBE_TIMEOUT_SECONDS,
        },
    )


async def _check_arq() -> HealthCheckResult:
    pool = get_arq_pool()
    if pool is None:
        return make_health_result("skipped", "arq disabled")
    try:
        await cast(_Pingable, pool).ping()
    except Exception as exc:
        return make_health_result("fail", f"arq pool ping failed: {exc}")
    return make_health_result("ok", "arq pool reachable")


async def _check_storage() -> HealthCheckResult:
    app_settings = get_app_settings()
    storage_settings = get_storage_settings()
    ok, message = await check_storage(timeout_seconds=app_settings.S3_PROBE_TIMEOUT_SECONDS)
    details: dict[str, object] = {
        "backend": storage_settings.STORAGE_BACKEND.value,
        "timeout_seconds": app_settings.S3_PROBE_TIMEOUT_SECONDS,
    }
    if storage_settings.STORAGE_BACKEND == StorageBackend.S3:
        details["bucket"] = storage_settings.S3_BUCKET
        if storage_settings.S3_ENDPOINT:
            details["endpoint"] = storage_settings.S3_ENDPOINT
    else:
        details["root"] = storage_settings.FILESYSTEM_ROOT

    return make_health_result(
        "ok" if ok else "fail",
        "storage probe ok" if ok else f"storage probe failed: {message}",
        details=details,
    )


async def _check_service_registration(
    registration: ServiceRegistration,
    runtime_service: RuntimeService | None,
) -> HealthCheckResult:
    details: dict[str, object] = {}
    messages: list[str] = []
    status: HealthStatus = "ok"

    startup_states, startup_ok = service_startup_states(runtime_service)
    if startup_states:
        details["startup_results"] = startup_states
        messages.append("startup hooks checked")
        if not startup_ok:
            status = "fail"

    runtime_config_hook = getattr(registration, "runtime_config_hook", None)
    if callable(runtime_config_hook):
        try:
            service_runtime_config = await asyncio.to_thread(runtime_config_hook)
        except Exception as exc:
            return make_health_result(
                "fail",
                f"{registration.name} runtime config hook failed: {exc}",
                details=details,
            )
        if not isinstance(service_runtime_config, Mapping):
            return make_health_result(
                "fail",
                f"{registration.name} runtime config hook must return a mapping",
                details=details,
            )
        service_runtime_config = cast(Mapping[str, object], service_runtime_config)
        details["runtime_config_sections"] = sorted(service_runtime_config.keys())
        details["runtime_config_section_count"] = len(service_runtime_config)
        messages.append("runtime config loaded")

    if status == "ok" and not messages:
        return make_health_result(
            "skipped",
            f"{registration.name} has no diagnostics hooks",
            details=details,
        )

    if status == "ok":
        return make_health_result(
            "ok",
            f"{registration.name}: {', '.join(messages)}",
            details=details,
        )

    return make_health_result(
        "fail",
        f"{registration.name} diagnostics failed",
        details=details,
    )


async def _collect_health_checks(request: Request) -> dict[str, HealthCheckResult]:
    app_check = _check_app_state(request)
    database_check, storage_check, arq_check = await asyncio.gather(_check_database(), _check_storage(), _check_arq())

    checks: dict[str, HealthCheckResult] = {
        "app": app_check,
        "database": database_check,
        "storage": storage_check,
        "arq": arq_check,
    }

    runtime_services = _collect_runtime_services(request)
    service_registrations = getattr(request.app.state, "service_registrations", [])
    if service_registrations:
        service_checks = await asyncio.gather(
            *[
                _check_service_registration(registration, runtime_services.get(registration.name))
                for registration in service_registrations
            ]
        )
        for registration, result in zip(service_registrations, service_checks, strict=True):
            checks[f"service.{registration.name}"] = result

    return checks


def _health_status(checks: Mapping[str, HealthCheckResult]) -> HealthStatus:
    return health_status(checks)


@router.get("/health", response_model=HealthResponse, summary="Service readiness")
@router.get("/health/ready", response_model=HealthResponse, summary="Service readiness")
async def readiness(request: Request, response: Response) -> HealthResponse:
    checks = await _collect_health_checks(request)
    status = _health_status(checks)
    if status == "fail":
        response.status_code = 503

    return HealthResponse(status=status, checks=checks, config=_serialize_health_config())


@router.get("/health/live", response_model=HealthLiveResponse, summary="Service liveness")
async def liveness(request: Request) -> HealthLiveResponse:
    checks = _collect_liveness_checks(request)
    return HealthLiveResponse(status="ok", checks=checks)
