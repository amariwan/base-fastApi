from __future__ import annotations

"""Build redacted healthcheck configuration payloads."""

from fastapi import HTTPException, status

from config import get_app_settings, get_db_settings
from shared.logging.AppLogger import system_logger as syslog

from .schemas import HealthConfig


def _log_level_value(raw_level: object) -> str:
    value = getattr(raw_level, "value", raw_level)
    return str(value).upper()


def build_safe_health_config() -> HealthConfig:
    """Return a sanitized snapshot of app/db configuration."""
    try:
        app_cfg = get_app_settings()
        db_cfg = get_db_settings()
        payload = {
            "APP_SETTINGS": {
                "LOG_LEVEL": _log_level_value(getattr(app_cfg, "LOG_LEVEL", "INFO")),
                "TEST_MODE": bool(getattr(app_cfg, "TEST_MODE", False)),
            },
            "DB_SETTINGS": {
                "DB_PORT": int(getattr(db_cfg, "DB_PORT", 0) or 0),
                "DB_DATABASE": str(getattr(db_cfg, "DB_DATABASE", "")),
            },
        }
        return HealthConfig.model_validate(payload)
    except Exception as exc:
        syslog.exception("health_config_error", extra={"etype": type(exc).__name__})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="unavailable",
        ) from exc
