import asyncio
import logging
from collections.abc import Mapping
from typing import TypeGuard, cast

from app.config import AppSettings, DbSettings, get_app_settings, get_db_settings
from app.core.core_auth import CurrentUser, require_admin
from app.core.core_auth.settings import AuthSettings, RoleSettings, get_auth_settings, get_role_settings
from app.core.core_extensions.loader import RuntimeService, ServiceRegistration
from app.core.core_storage.settings import StorageBackend, StorageSettings, get_storage_settings
from app.core.startup_checks import check_db
from app.core.startup_checks import check_s3 as check_storage
from fastapi import APIRouter, Depends, Request, Response

from .schemas import (
    HealthCheckResult,
    HealthCheckStatus,
    HealthConfig,
    HealthLiveResponse,
    HealthResponse,
    HealthSettingsApp,
    HealthSettingsDB,
    HealthStatus,
    RuntimeConfigResponse,
    RuntimeConfigSection,
    RuntimeConfigValue,
    ServiceRuntimeConfig,
    WhoAmIResponse,
)

logger = logging.getLogger("app_logger")

router = APIRouter(tags=["health"])
healthcheck_router = router

_SECRET_FIELDS_BY_SECTION: dict[str, frozenset[str]] = {
    "app": frozenset({"AUTH_HS_SECRET"}),
    "db": frozenset({"DB_PASSWORD"}),
    "auth": frozenset({"HS_SECRET"}),
    "storage": frozenset({"accessKey", "secretKey", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"}),
}

_STORAGE_ALIAS_KEYS: dict[str, str] = {
    "S3_ACCESS_KEY_ID": "accessKey",
    "S3_SECRET_ACCESS_KEY": "secretKey",
}


def _redact_secret(value: RuntimeConfigValue) -> RuntimeConfigValue:
    if value in (None, ""):
        return None
    return "***"


def _json_list(values: list[str]) -> list[str]:
    return [value for value in values]


def _is_string_list(value: object) -> TypeGuard[list[str]]:
    if not isinstance(value, list):
        return False
    for item in cast(list[object], value):
        if not isinstance(item, str):
            return False
    return True


def _encode_runtime_value(value: object) -> RuntimeConfigValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if _is_string_list(value):
        return [item for item in value]
    raise TypeError(f"Unsupported runtime config value type: {type(value).__name__}")


def _to_runtime_section(payload: Mapping[str, object]) -> RuntimeConfigSection:
    return {key: _encode_runtime_value(value) for key, value in payload.items()}


def _redact_section(section: str, payload: RuntimeConfigSection) -> RuntimeConfigSection:
    for field in _SECRET_FIELDS_BY_SECTION.get(section, frozenset()):
        if field in payload:
            payload[field] = _redact_secret(payload[field])
    return payload


def _serialize_app_settings(settings: AppSettings) -> RuntimeConfigSection:
    payload = _to_runtime_section(settings.model_dump(mode="json"))
    payload["AUTH_ALGORITHMS_RESOLVED"] = _json_list(settings.auth_algorithms)
    payload["CORS_ALLOWED_ORIGINS_RESOLVED"] = _json_list(settings.cors_allowed_origins)
    payload["CORS_ALLOW_METHODS_RESOLVED"] = _json_list(settings.cors_allow_methods)
    payload["CORS_ALLOW_HEADERS_RESOLVED"] = _json_list(settings.cors_allow_headers)
    return _redact_section("app", payload)


def _serialize_db_settings(settings: DbSettings) -> RuntimeConfigSection:
    payload = _to_runtime_section(settings.model_dump(mode="json"))
    return _redact_section("db", payload)


def _serialize_auth_settings(settings: AuthSettings) -> RuntimeConfigSection:
    payload = _to_runtime_section(settings.model_dump(mode="json"))
    return _redact_section("auth", payload)


def _serialize_role_settings(settings: RoleSettings) -> RuntimeConfigSection:
    return _to_runtime_section(settings.model_dump(mode="json"))


def _serialize_storage_settings(settings: StorageSettings) -> RuntimeConfigSection:
    payload = _to_runtime_section(settings.model_dump(mode="json"))
    for canonical_key, alias_key in _STORAGE_ALIAS_KEYS.items():
        if canonical_key in payload:
            payload[alias_key] = payload[canonical_key]
    return _redact_section("storage", payload)


def _collect_runtime_config_sections(request: Request) -> ServiceRuntimeConfig:
    runtime_config: ServiceRuntimeConfig = {}
    for registration in getattr(request.app.state, "service_registrations", []):
        runtime_config_hook = getattr(registration, "runtime_config_hook", None)
        if not callable(runtime_config_hook):
            continue
        try:
            service_runtime_config = runtime_config_hook()
        except Exception:
            logger.exception("Runtime config hook failed")
            continue
        if not isinstance(service_runtime_config, Mapping):
            logger.warning("Runtime config hook must return a mapping")
            continue
        runtime_config.update(cast(ServiceRuntimeConfig, service_runtime_config))
    return runtime_config


def _redacted_field_names() -> list[str]:
    return sorted(f"{section}.{field}" for section, fields in _SECRET_FIELDS_BY_SECTION.items() for field in fields)


def _make_health_result(
    status: HealthCheckStatus,
    message: str,
    *,
    details: Mapping[str, object] | None = None,
) -> HealthCheckResult:
    return HealthCheckResult(status=status, message=message, details=_to_runtime_section(details or {}))


def _collect_runtime_services(request: Request) -> dict[str, RuntimeService]:
    runtime_services = getattr(request.app.state, "runtime_services", [])
    return {runtime_service.registration.name: runtime_service for runtime_service in runtime_services}


def _service_startup_states(runtime_service: RuntimeService | None) -> tuple[list[str], bool]:
    if runtime_service is None:
        return [], True

    states: list[str] = []
    ok = True
    for result in runtime_service.startup_results:
        if result is None or isinstance(result, (bool, int, float, str)):
            states.append("completed")
            continue
        if isinstance(result, Exception):
            states.append(f"failed: {result}")
            ok = False
            continue
        if isinstance(result, asyncio.Future):
            if result.cancelled():
                states.append("cancelled")
                ok = False
                continue
            if not result.done():
                states.append("running")
                continue
            task_exception = result.exception()
            if task_exception is not None:
                states.append(f"failed: {task_exception}")
                ok = False
                continue
            states.append("completed")
            continue
        states.append(type(result).__name__)
    return states, ok


def _serialize_health_config() -> HealthConfig | None:
    db_settings = get_db_settings()
    if not db_settings.DB_ENABLED:
        return None

    app_settings = get_app_settings()
    return HealthConfig(
        app=HealthSettingsApp(log_level=app_settings.LOG_LEVEL.value, test_mode=app_settings.TEST_MODE),
        db=HealthSettingsDB(port=cast(int, db_settings.DB_PORT), database=cast(str, db_settings.DB_DATABASE)),
    )


def _check_app_state(request: Request) -> HealthCheckResult:
    app_settings = get_app_settings()
    db_settings = get_db_settings()
    storage_settings = get_storage_settings()
    service_registrations = getattr(request.app.state, "service_registrations", [])
    runtime_services = getattr(request.app.state, "runtime_services", [])
    return _make_health_result(
        "ok",
        "application settings loaded",
        details={
            "api_prefix": app_settings.API_PREFIX,
            "auth_mode": app_settings.AUTH_MODE,
            "db_enabled": db_settings.DB_ENABLED,
            "log_level": app_settings.LOG_LEVEL.value,
            "runtime_services": len(runtime_services),
            "service_registrations": len(service_registrations),
            "storage_backend": storage_settings.STORAGE_BACKEND.value,
            "test_mode": app_settings.TEST_MODE,
        },
    )


def _collect_liveness_checks(request: Request) -> dict[str, HealthCheckResult]:
    return {"app": _check_app_state(request)}


async def _check_database() -> HealthCheckResult:
    db_settings = get_db_settings()
    if not db_settings.DB_ENABLED:
        return _make_health_result("skipped", "database disabled", details={"enabled": False})

    app_settings = get_app_settings()
    ok, message = await check_db(timeout_seconds=app_settings.DB_PROBE_TIMEOUT_SECONDS)
    return _make_health_result(
        "ok" if ok else "fail",
        "database probe ok" if ok else f"database probe failed: {message}",
        details={
            "database": cast(str, db_settings.DB_DATABASE),
            "enabled": True,
            "port": cast(int, db_settings.DB_PORT),
            "timeout_seconds": app_settings.DB_PROBE_TIMEOUT_SECONDS,
        },
    )


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

    return _make_health_result(
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

    startup_states, startup_ok = _service_startup_states(runtime_service)
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
            return _make_health_result(
                "fail",
                f"{registration.name} runtime config hook failed: {exc}",
                details=details,
            )
        if not isinstance(service_runtime_config, Mapping):
            return _make_health_result(
                "fail",
                f"{registration.name} runtime config hook must return a mapping",
                details=details,
            )
        details["runtime_config_sections"] = sorted(service_runtime_config.keys())
        details["runtime_config_section_count"] = len(service_runtime_config)
        messages.append("runtime config loaded")

    if status == "ok" and not messages:
        return _make_health_result(
            "skipped",
            f"{registration.name} has no diagnostics hooks",
            details=details,
        )

    if status == "ok":
        return _make_health_result(
            "ok",
            f"{registration.name}: {', '.join(messages)}",
            details=details,
        )

    return _make_health_result(
        "fail",
        f"{registration.name} diagnostics failed",
        details=details,
    )


async def _collect_health_checks(request: Request) -> dict[str, HealthCheckResult]:
    app_check = _check_app_state(request)
    database_check, storage_check = await asyncio.gather(_check_database(), _check_storage())

    checks: dict[str, HealthCheckResult] = {
        "app": app_check,
        "database": database_check,
        "storage": storage_check,
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
    if any(result.status == "fail" for result in checks.values()):
        return "fail"
    return "ok"


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


@router.get("/whoami", response_model=WhoAmIResponse)
async def whoami(user: CurrentUser) -> WhoAmIResponse:
    """Return the normalized user claims."""
    payload = WhoAmIResponse(
        sub=user.sub,
        name=user.name,
        email=user.email,
        preferred_username=user.preferred_username,
        organisation=user.organisation,
        roles=list(user.roles),
    )
    logger.debug("whoami", extra={"roles_count": len(payload.roles)})
    return payload


@router.get(
    "/runtime-config",
    response_model=RuntimeConfigResponse,
    summary="Current runtime configuration",
    tags=["configuration"],
    dependencies=[Depends(require_admin)],
)
async def runtime_config(request: Request) -> RuntimeConfigResponse:
    service_runtime_config = _collect_runtime_config_sections(request)
    return RuntimeConfigResponse(
        app=_serialize_app_settings(get_app_settings()),
        db=_serialize_db_settings(get_db_settings()),
        auth=_serialize_auth_settings(get_auth_settings()),
        roles=_serialize_role_settings(get_role_settings()),
        storage=_serialize_storage_settings(get_storage_settings()),
        services=service_runtime_config,
        redacted_fields=_redacted_field_names(),
    )
