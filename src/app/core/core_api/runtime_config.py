import logging
from collections.abc import Mapping
from typing import TypeGuard, cast

from fastapi import APIRouter, Depends, Request

from app.config import AppSettings, DbSettings, get_app_settings, get_db_settings
from app.core.core_api.schemas import (
    RuntimeConfigResponse,
    RuntimeConfigSection,
    RuntimeConfigValue,
    ServiceRuntimeConfig,
)
from app.core.core_auth import require_admin
from app.core.core_auth.settings import AuthSettings, RoleSettings, get_auth_settings, get_role_settings
from app.core.core_storage.settings import StorageSettings, get_storage_settings

logger = logging.getLogger("app_logger")

router = APIRouter(tags=["configuration"])
runtime_config_router = router

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


@router.get(
    "/runtime-config",
    response_model=RuntimeConfigResponse,
    summary="Current runtime configuration",
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
