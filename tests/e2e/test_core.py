from app.views import app
from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["app"]["status"] == "ok"
    assert payload["checks"]["database"]["status"] == "skipped"
    assert payload["checks"]["storage"]["status"] == "ok"
    assert any(key.startswith("service.") for key in payload["checks"])


def test_health_live_endpoint_returns_ok():
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["app"]["status"] == "ok"
    assert list(payload["checks"].keys()) == ["app"]


def test_health_ready_alias_returns_ok():
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["database"]["status"] == "skipped"
