from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.factory import create_app
from core.lifespan import lifespan
from core.middleware import register_middleware
from core.openapi import add_bearer_security, simplify_operation_ids
from core.routes import API_ROOT, build_api_router, register_routers
from db import db


def test_build_api_router_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PREFIX", "/api")
    router = build_api_router()
    assert router.prefix == API_ROOT

    app = FastAPI()
    register_routers(app)
    register_routers(app)  # idempotent
    assert any(route.path == f"{API_ROOT}/health" for route in app.router.routes)


def test_openapi_helpers() -> None:
    app = FastAPI()

    @app.get("/ping", name="do_ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    simplify_operation_ids(app)
    add_bearer_security(app)
    schema = app.openapi()
    assert schema["paths"]["/ping"]["get"]["operationId"] == "do_ping"
    assert "BearerAuth" in schema["components"]["securitySchemes"]


@pytest.mark.asyncio
async def test_lifespan_initializes_and_disposes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_init_models(*, drop: bool = False) -> None:
        calls.append("init")

    async def fake_dispose() -> None:
        calls.append("dispose")

    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("TEST_MODE", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setattr(db, "init_models", fake_init_models)
    monkeypatch.setattr(db, "dispose", fake_dispose)

    app = FastAPI()
    async with lifespan(app):
        pass

    assert calls == ["init", "dispose"]


def test_register_middleware_adds_security_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    app = FastAPI()

    @app.get("/headers")
    async def headers() -> dict[str, str]:
        return {"ok": "true"}

    register_middleware(app)
    client = TestClient(app)
    response = client.get("/headers")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_create_app_builds_fastapi_instance() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
