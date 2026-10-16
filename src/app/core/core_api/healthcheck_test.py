"""Healthcheck tests, including intentionally white-box diagnostic coverage."""

# These tests exercise private diagnostic seams directly to avoid network probes.
# pyright: reportPrivateUsage=false

import asyncio
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import FastAPI, Request
from starlette.datastructures import State

from app.core.core_api import healthcheck
from app.core.core_extensions.loader import ServiceRegistration


def test_check_service_registration_collects_runtime_config() -> None:
    """
    _check_service_registration should call the runtime_config_hook and populate
    the details of the HealthCheckResult.
    """
    registration = ServiceRegistration(
        name="docgen",
        runtime_config_hook=lambda: {"render": {"default_output_format": "pdf"}},
    )

    result = asyncio.run(healthcheck._check_service_registration(registration, None))

    assert result.status == "ok"
    assert "runtime config loaded" in result.message
    assert result.details["runtime_config_sections"] == ["render"]
    assert result.details["runtime_config_section_count"] == 1


def test_collect_liveness_checks_does_not_probe_external_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_db(*args: object, **kwargs: object) -> None:
        raise AssertionError("db probe")

    def fail_storage(*args: object, **kwargs: object) -> None:
        raise AssertionError("storage probe")

    monkeypatch.setattr(healthcheck, "check_db", fail_db)
    monkeypatch.setattr(healthcheck, "check_storage", fail_storage)

    app = FastAPI()
    request: Request[State] = cast(Request[State], type("Request", (), {"app": app})())

    result = healthcheck._collect_liveness_checks(request)

    assert result["app"].status == "ok"
    assert result["app"].message == "application settings loaded"
    assert list(result) == ["app"]


def test_check_app_state_uses_canonical_auth_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    app_settings = SimpleNamespace(
        API_PREFIX="/api",
        AUTH_MODE="jwks",
        LOG_LEVEL=SimpleNamespace(value="INFO"),
        TEST_MODE=False,
    )
    db_settings = SimpleNamespace(DB_ENABLED=False, DB_PORT=5432, DB_DATABASE="app")
    storage_settings = SimpleNamespace(STORAGE_BACKEND=SimpleNamespace(value="filesystem"))

    monkeypatch.setattr(healthcheck, "get_app_settings", lambda: app_settings)
    monkeypatch.setattr(healthcheck, "get_auth_settings", lambda: SimpleNamespace(MODE="hs"))
    monkeypatch.setattr(healthcheck, "get_db_settings", lambda: db_settings)
    monkeypatch.setattr(healthcheck, "get_storage_settings", lambda: storage_settings)

    request: Request[State] = cast(Request[State], type("Request", (), {"app": FastAPI()})())
    result = healthcheck._check_app_state(request)

    assert result.details["auth_mode"] == "hs"
