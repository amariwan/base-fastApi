from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.factory import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_health_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "config": None}


def test_health_config_requires_admin(client: TestClient, monkeypatch, hs_token) -> None:
    monkeypatch.setenv("TEST_MODE", "false")
    monkeypatch.setenv("ROLE_ADMIN_ROLES", "admin")
    response = client.get("/api/v1/health?config=true")
    assert response.status_code == 403

    token = hs_token({"roles": ["admin"]})
    response = client.get(
        "/api/v1/health?config=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["config"]["APP_SETTINGS"]["LOG_LEVEL"]


def test_whoami_endpoint(client: TestClient, hs_token) -> None:
    token = hs_token({"email": "user@example.com", "name": "User"})
    response = client.get(
        "/api/v1/whoami",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["sub"] == "user-123"


def test_health_config_allowed_in_test_mode(monkeypatch) -> None:
    monkeypatch.setenv("TEST_MODE", "true")
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health?config=true")
        assert response.status_code == 200
