from __future__ import annotations

"""Schemas returned by the healthcheck endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr


class HealthSettingsApp(BaseModel):
    """Minimal application configuration exposed via /health."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    log_level: StrictStr = Field(..., alias="LOG_LEVEL")
    test_mode: StrictBool = Field(..., alias="TEST_MODE")


class HealthSettingsDB(BaseModel):
    """Minimal database configuration exposed via /health."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    port: StrictInt = Field(..., alias="DB_PORT", ge=0)
    database: StrictStr = Field(..., alias="DB_DATABASE")


class HealthConfig(BaseModel):
    """Combined app+db view for diagnostics."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    app: HealthSettingsApp = Field(..., alias="APP_SETTINGS")
    db: HealthSettingsDB = Field(..., alias="DB_SETTINGS")


class HealthResponse(BaseModel):
    """Payload returned by /health."""

    status: Literal["ok"] = "ok"
    config: HealthConfig | None = None


class WhoAmIResponse(BaseModel):
    """Normalized user identity response."""

    sub: StrictStr | None = None
    name: StrictStr | None = None
    email: StrictStr | None = None
    preferred_username: StrictStr | None = None
    organization: StrictStr | None = None
    roles: list[StrictStr] = Field(default_factory=list)


__all__ = [
    "HealthResponse",
    "WhoAmIResponse",
    "HealthConfig",
    "HealthSettingsApp",
    "HealthSettingsDB",
]

