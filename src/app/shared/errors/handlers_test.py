"""Tests for unified exception handlers."""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.shared.errors.exceptions import UnifiedApiError
from app.shared.errors.handlers import install_unified_exception_handlers


def _make_app() -> FastAPI:
    app = FastAPI()
    install_unified_exception_handlers(app)

    @app.get("/raise-unified")
    async def raise_unified() -> None:
        raise UnifiedApiError("TEMPLATE_NOT_FOUND")

    @app.get("/raise-unified-details")
    async def raise_unified_details() -> None:
        raise UnifiedApiError(
            "VALIDATION_FAILED",
            details=[{"field": "name", "reason": "required"}],
        )

    @app.get("/raise-unified-custom")
    async def raise_unified_custom() -> None:
        raise UnifiedApiError(
            "SERVER_ERROR",
            message="Benutzerdefinierter Fehler",
            type="warning",
            http_status=503,
        )

    class StrictModel(BaseModel):
        name: str

    @app.post("/validate")
    async def validate(payload: StrictModel) -> dict:
        return {"name": payload.name}

    return app


class TestUnifiedApiErrorHandler:
    def test_returns_unified_envelope(self) -> None:
        client = TestClient(_make_app())
        resp = client.get("/raise-unified")
        assert resp.status_code == 404

        body = resp.json()
        assert "error" in body
        error = body["error"]
        assert error["code"] == "TEMPLATE_NOT_FOUND"
        assert error["type"] == "error"
        assert "traceId" in error
        assert "timestamp" in error

    def test_includes_details(self) -> None:
        client = TestClient(_make_app())
        resp = client.get("/raise-unified-details")
        assert resp.status_code == 400

        error = resp.json()["error"]
        assert error["code"] == "VALIDATION_FAILED"
        assert error["type"] == "warning"
        assert len(error["details"]) == 1
        assert error["details"][0]["field"] == "name"

    def test_custom_overrides(self) -> None:
        client = TestClient(_make_app())
        resp = client.get("/raise-unified-custom")
        assert resp.status_code == 503

        error = resp.json()["error"]
        assert error["message"] == "Benutzerdefinierter Fehler"
        assert error["type"] == "warning"


class TestValidationErrorHandler:
    def test_pydantic_validation_returns_unified(self) -> None:
        client = TestClient(_make_app())
        resp = client.post("/validate", content=json.dumps({}))
        assert resp.status_code == 400

        body = resp.json()
        assert "error" in body
        error = body["error"]
        assert error["code"] == "VALIDATION_FAILED"
        assert error["type"] == "warning"
        assert isinstance(error["details"], list)
        assert len(error["details"]) >= 1


class TestIdempotentInstall:
    def test_double_install_is_noop(self) -> None:
        app = FastAPI()
        install_unified_exception_handlers(app)
        install_unified_exception_handlers(app)
        # No error — marker prevents double registration
