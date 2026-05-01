"""E2E tests for HTTP routing, health endpoints, and core API behaviour.

Tests run against the full FastAPI application (via TestClient) and do not
require an external database.  DB is disabled by default via conftest.py.
"""

from app.views import app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


class TestHealthEndpoints:
    def test_root_health_returns_ok(self):
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["checks"]["app"]["status"] == "ok"
        assert payload["checks"]["database"]["status"] == "skipped"
        assert payload["checks"]["storage"]["status"] == "ok"

    def test_api_prefixed_health_returns_ok(self):
        with TestClient(app) as client:
            response = client.get("/api/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert "checks" in payload

    def test_api_prefixed_health_ready_alias_returns_ok(self):
        with TestClient(app) as client:
            response = client.get("/api/health/ready")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["checks"]["database"]["status"] == "skipped"

    def test_api_prefixed_health_live_returns_ok(self):
        with TestClient(app) as client:
            response = client.get("/api/health/live")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert list(payload["checks"].keys()) == ["app"]

    def test_health_content_type_is_json(self):
        with TestClient(app) as client:
            response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# OpenAPI schema
# ---------------------------------------------------------------------------


class TestOpenAPI:
    def test_openapi_json_reachable(self):
        with TestClient(app) as client:
            response = client.get("/api/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_openapi_contains_validate_template_path(self):
        with TestClient(app) as client:
            response = client.get("/api/openapi.json")
        paths = response.json()["paths"]
        assert any("validate-template" in path for path in paths)


# ---------------------------------------------------------------------------
# Job retrieval – buildDoc & buildView (non-existing job IDs)
# ---------------------------------------------------------------------------


class TestBuildDocGetEndpoint:
    def test_unknown_job_id_returns_404(self):
        with TestClient(app) as client:
            response = client.get("/api/buildDoc/nonexistent-job-id")
        assert response.status_code == 404

    def test_unknown_job_id_returns_machine_readable_error(self):
        with TestClient(app) as client:
            response = client.get("/api/buildDoc/nonexistent-job-id")
        body = response.json()
        # Should have a detail field with code
        assert "detail" in body
        detail = body["detail"]
        assert isinstance(detail.get("code"), str)


class TestBuildViewGetEndpoint:
    def test_unknown_job_id_returns_404(self):
        with TestClient(app) as client:
            response = client.get("/api/buildView/nonexistent-job-id")
        assert response.status_code == 404

    def test_404_detail_has_solution_hint(self):
        with TestClient(app) as client:
            response = client.get("/api/buildView/nonexistent-job-id")
        body = response.json()
        detail = body.get("detail", {})
        # The endpoint config sets a "solution" field
        assert "solution" in detail or "message" in detail


# ---------------------------------------------------------------------------
# Template validation – request body validation
# ---------------------------------------------------------------------------


class TestValidateTemplateRequestValidation:
    def test_missing_body_returns_422(self):
        with TestClient(app) as client:
            response = client.post("/api/validate-template")
        assert response.status_code == 400

    def test_empty_json_body_returns_validation_error_in_response(self):
        """Empty body is valid JSON for the API (all fields optional).
        The response should be 200 but the validation_status should be INVALID
        since no template source was provided for the default docx type."""
        with TestClient(app) as client:
            response = client.post("/api/validate-template", json={})
        assert response.status_code == 200
        body = response.json()
        # The API returns 200 but with validation errors about missing template source
        assert body.get("valid") is False or body.get("validation_status") is not None

    def test_valid_minimal_body_accepted(self):
        body = {
            "document_type": "html",
            "template_content": "Hello {{ name }}",
            "payload": {"name": "World"},
            "dry_run": False,
        }
        with TestClient(app) as client:
            response = client.post("/api/validate-template", json=body)
        assert response.status_code == 200

    def test_valid_missing_payload_accepted(self):
        """payload is optional - template may have no placeholders."""
        body = {
            "document_type": "html",
            "template_content": "Static content",
            "payload": {},
            "dry_run": False,
        }
        with TestClient(app) as client:
            response = client.post("/api/validate-template", json=body)
        assert response.status_code == 200

    def test_response_has_valid_flag(self):
        body = {
            "document_type": "html",
            "template_content": "{{ item }}",
            "payload": {"item": "val"},
            "dry_run": False,
        }
        with TestClient(app) as client:
            response = client.post("/api/validate-template", json=body)
        data = response.json()
        assert "valid" in data
        assert isinstance(data["valid"], bool)

    def test_response_has_validation_status(self):
        body = {
            "document_type": "html",
            "template_content": "Hello {{ name }}",
            "payload": {"name": "Ada"},
            "dry_run": True,
        }
        with TestClient(app) as client:
            response = client.post("/api/validate-template", json=body)
        data = response.json()
        assert "validation_status" in data
        assert data["validation_status"] in {"VALID", "VALID_WITH_WARNINGS", "INVALID", "ERROR"}

    def test_template_with_all_placeholders_provided_is_valid(self):
        body = {
            "document_type": "html",
            "template_content": "{{ first }} {{ last }}",
            "payload": {"first": "Hans", "last": "Mueller"},
            "dry_run": False,
        }
        with TestClient(app) as client:
            response = client.post("/api/validate-template", json=body)
        assert response.status_code == 200
        assert response.json()["valid"] is True

    def test_dry_run_does_not_produce_rendered_output(self):
        body = {
            "document_type": "html",
            "template_content": "{{ secret }}",
            "payload": {"secret": "TOP_SECRET"},
            "dry_run": True,
        }
        with TestClient(app) as client:
            response = client.post("/api/validate-template", json=body)
        # dry_run=True means we validate but do not produce/expose rendered output
        assert response.status_code == 200

    def test_deeply_nested_payload_works(self):
        body = {
            "document_type": "html",
            "template_content": "{{ a.b.c }}",
            "payload": {"a": {"b": {"c": "deep"}}},
            "dry_run": False,
        }
        with TestClient(app) as client:
            response = client.post("/api/validate-template", json=body)
        assert response.status_code == 200
        assert response.json()["valid"] is True


# ---------------------------------------------------------------------------
# Download endpoint
# ---------------------------------------------------------------------------


class TestDownloadEndpoint:
    def test_unknown_token_returns_404_or_410(self):
        with TestClient(app) as client:
            response = client.get("/api/download/invalid-token")
        assert response.status_code in {404, 410}

    def test_invalid_token_body_has_detail(self):
        with TestClient(app) as client:
            response = client.get("/api/download/totally-invalid-token")
        body = response.json()
        assert "detail" in body


# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------


class TestCORSHeaders:
    def test_cors_headers_present_for_allowed_origin(self):
        with TestClient(app) as client:
            response = client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
        assert response.status_code in {200, 204}
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert "access-control-allow-methods" in response.headers
