"""Tests for http_security_middleware registrations."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _simple_app() -> FastAPI:
    """Return a minimal FastAPI app with one GET endpoint."""
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


# --------------------------------------------------------------------------- #
# Logging middleware
# --------------------------------------------------------------------------- #
class TestHttpLoggingMiddleware:
    def test_disabled_does_not_register(self):
        from app.core.core_middleware.http_security_middleware import register_http_logging_middleware

        app = _simple_app()
        register_http_logging_middleware(
            app,
            enabled=False,
            request_logging_enabled=True,
            response_logging_enabled=True,
            fault_logging_enabled=True,
        )
        client = TestClient(app)
        # If no error, middleware registration was skipped gracefully
        response = client.get("/ping")
        assert response.status_code == 200

    def test_enabled_passes_request_through(self):
        from app.core.core_middleware.http_security_middleware import register_http_logging_middleware

        app = _simple_app()
        register_http_logging_middleware(
            app,
            enabled=True,
            request_logging_enabled=True,
            response_logging_enabled=True,
            fault_logging_enabled=True,
        )
        client = TestClient(app)
        response = client.get("/ping")
        assert response.status_code == 200

    def test_enabled_logging_disabled_passes_through(self):
        from app.core.core_middleware.http_security_middleware import register_http_logging_middleware

        app = _simple_app()
        register_http_logging_middleware(
            app,
            enabled=True,
            request_logging_enabled=False,
            response_logging_enabled=False,
            fault_logging_enabled=False,
        )
        client = TestClient(app)
        response = client.get("/ping")
        assert response.status_code == 200

    def test_exception_is_re_raised_with_fault_logging(self):
        from app.core.core_middleware.http_security_middleware import register_http_logging_middleware

        app = FastAPI()

        @app.get("/boom")
        async def boom():
            raise ValueError("intentional")

        register_http_logging_middleware(
            app,
            enabled=True,
            request_logging_enabled=False,
            response_logging_enabled=False,
            fault_logging_enabled=True,
        )
        client = TestClient(app, raise_server_exceptions=True)
        with pytest.raises(ValueError, match="intentional"):
            client.get("/boom")


# --------------------------------------------------------------------------- #
# API-key middleware
# --------------------------------------------------------------------------- #
class TestApiKeyMiddleware:
    def test_disabled_lets_request_through(self):
        from app.core.core_middleware.http_security_middleware import register_api_key_middleware

        app = _simple_app()
        register_api_key_middleware(app, enabled=False, header_name="X-API-Key", expected_api_key="secret")
        client = TestClient(app)
        assert client.get("/ping").status_code == 200

    def test_enabled_correct_key_passes(self):
        from app.core.core_middleware.http_security_middleware import register_api_key_middleware

        app = _simple_app()
        register_api_key_middleware(app, enabled=True, header_name="X-API-Key", expected_api_key="mysecret")
        client = TestClient(app)
        assert client.get("/ping", headers={"X-API-Key": "mysecret"}).status_code == 200

    def test_enabled_wrong_key_returns_401(self):
        from app.core.core_middleware.http_security_middleware import register_api_key_middleware

        app = _simple_app()
        register_api_key_middleware(app, enabled=True, header_name="X-API-Key", expected_api_key="correct")
        client = TestClient(app)
        response = client.get("/ping", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

    def test_enabled_missing_key_returns_401(self):
        from app.core.core_middleware.http_security_middleware import register_api_key_middleware

        app = _simple_app()
        register_api_key_middleware(app, enabled=True, header_name="X-API-Key", expected_api_key="correct")
        client = TestClient(app)
        assert client.get("/ping").status_code == 401

    def test_enabled_empty_api_key_configured_returns_500(self):
        from app.core.core_middleware.http_security_middleware import register_api_key_middleware

        app = _simple_app()
        register_api_key_middleware(app, enabled=True, header_name="X-API-Key", expected_api_key=None)
        client = TestClient(app)
        assert client.get("/ping").status_code == 500


# --------------------------------------------------------------------------- #
# Request size middleware
# --------------------------------------------------------------------------- #
class TestRequestSizeMiddleware:
    def test_request_within_limit_passes(self):
        from app.core.core_middleware.http_security_middleware import register_request_size_middleware

        app = FastAPI()

        @app.post("/upload")
        async def upload():
            return {"ok": True}

        register_request_size_middleware(app, max_request_size_bytes=100, max_upload_size_bytes=1000)
        client = TestClient(app)
        response = client.post(
            "/upload",
            content=b"small",
            headers={"content-length": "5", "content-type": "application/json"},
        )
        assert response.status_code == 200

    def test_request_over_limit_returns_413(self):
        from app.core.core_middleware.http_security_middleware import register_request_size_middleware

        app = FastAPI()

        @app.post("/upload")
        async def upload():
            return {"ok": True}  # pragma: no cover

        register_request_size_middleware(app, max_request_size_bytes=10, max_upload_size_bytes=100)
        client = TestClient(app)
        response = client.post(
            "/upload",
            content=b"X" * 50,
            headers={"content-length": "50", "content-type": "application/json"},
        )
        assert response.status_code == 413

    def test_multipart_uses_upload_limit(self):
        from app.core.core_middleware.http_security_middleware import register_request_size_middleware

        app = FastAPI()

        @app.post("/upload")
        async def upload():
            return {"ok": True}  # pragma: no cover

        # max_upload is smaller than body, so should 413
        register_request_size_middleware(app, max_request_size_bytes=9999, max_upload_size_bytes=10)
        client = TestClient(app)
        response = client.post(
            "/upload",
            content=b"X" * 50,
            headers={"content-length": "50", "content-type": "multipart/form-data; boundary=X"},
        )
        assert response.status_code == 413

    def test_no_content_length_header_passes(self):
        from app.core.core_middleware.http_security_middleware import register_request_size_middleware

        app = FastAPI()

        @app.post("/upload")
        async def upload():
            return {"ok": True}

        register_request_size_middleware(app, max_request_size_bytes=10, max_upload_size_bytes=10)
        client = TestClient(app)
        # Without content-length header middleware should pass through
        response = client.post("/upload")
        assert response.status_code == 200

    def test_invalid_content_length_treated_as_zero(self):
        from app.core.core_middleware.http_security_middleware import register_request_size_middleware

        app = FastAPI()

        @app.post("/upload")
        async def upload():
            return {"ok": True}

        register_request_size_middleware(app, max_request_size_bytes=10, max_upload_size_bytes=10)
        client = TestClient(app)
        # Invalid content-length should not crash
        response = client.post(
            "/upload",
            headers={"content-length": "not-a-number", "content-type": "application/json"},
        )
        assert response.status_code == 200


# --------------------------------------------------------------------------- #
# Security headers middleware
# --------------------------------------------------------------------------- #
class TestSecurityHeadersMiddleware:
    def test_disabled_does_not_add_headers(self):
        from app.core.core_middleware.http_security_middleware import (
            SecurityHeadersConfig,
            register_security_headers_middleware,
        )

        app = _simple_app()
        cfg = SecurityHeadersConfig(
            enabled=False,
            hsts_enabled=True,
            hsts_max_age=31536000,
            csp_enabled=True,
            csp_directives="default-src 'self'",
        )
        register_security_headers_middleware(app, cfg)
        client = TestClient(app)
        resp = client.get("/ping")
        assert "X-Frame-Options" not in resp.headers

    def test_enabled_adds_base_security_headers(self):
        from app.core.core_middleware.http_security_middleware import (
            SecurityHeadersConfig,
            register_security_headers_middleware,
        )

        app = _simple_app()
        cfg = SecurityHeadersConfig(
            enabled=True,
            hsts_enabled=False,
            hsts_max_age=0,
            csp_enabled=False,
            csp_directives="",
            x_frame_options=None,
        )
        register_security_headers_middleware(app, cfg)
        client = TestClient(app)
        resp = client.get("/ping")
        assert "X-Frame-Options" not in resp.headers
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_x_frame_options_adds_header_when_configured(self):
        from app.core.core_middleware.http_security_middleware import (
            SecurityHeadersConfig,
            register_security_headers_middleware,
        )

        app = _simple_app()
        cfg = SecurityHeadersConfig(
            enabled=True,
            hsts_enabled=False,
            hsts_max_age=0,
            csp_enabled=False,
            csp_directives="",
            x_frame_options="DENY",
        )
        register_security_headers_middleware(app, cfg)
        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_x_frame_options_can_be_disabled(self):
        from app.core.core_middleware.http_security_middleware import (
            SecurityHeadersConfig,
            register_security_headers_middleware,
        )

        app = _simple_app()
        cfg = SecurityHeadersConfig(
            enabled=True,
            hsts_enabled=False,
            hsts_max_age=0,
            csp_enabled=False,
            csp_directives="",
            x_frame_options=None,
        )
        register_security_headers_middleware(app, cfg)
        client = TestClient(app)
        resp = client.get("/ping")
        assert "X-Frame-Options" not in resp.headers

    def test_hsts_enabled_adds_hsts_header(self):
        from app.core.core_middleware.http_security_middleware import (
            SecurityHeadersConfig,
            register_security_headers_middleware,
        )

        app = _simple_app()
        cfg = SecurityHeadersConfig(
            enabled=True,
            hsts_enabled=True,
            hsts_max_age=31536000,
            csp_enabled=False,
            csp_directives="",
        )
        register_security_headers_middleware(app, cfg)
        client = TestClient(app)
        resp = client.get("/ping")
        hsts = resp.headers.get("Strict-Transport-Security", "")
        assert "max-age=31536000" in hsts

    def test_csp_enabled_adds_csp_header(self):
        from app.core.core_middleware.http_security_middleware import (
            SecurityHeadersConfig,
            register_security_headers_middleware,
        )

        app = _simple_app()
        cfg = SecurityHeadersConfig(
            enabled=True,
            hsts_enabled=False,
            hsts_max_age=0,
            csp_enabled=True,
            csp_directives="default-src 'self'",
        )
        register_security_headers_middleware(app, cfg)
        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.headers.get("Content-Security-Policy") == "default-src 'self'"

    def test_csp_enabled_but_empty_directives_no_csp_header(self):
        from app.core.core_middleware.http_security_middleware import (
            SecurityHeadersConfig,
            register_security_headers_middleware,
        )

        app = _simple_app()
        cfg = SecurityHeadersConfig(
            enabled=True,
            hsts_enabled=False,
            hsts_max_age=0,
            csp_enabled=True,
            csp_directives="",  # empty → no CSP header
        )
        register_security_headers_middleware(app, cfg)
        client = TestClient(app)
        resp = client.get("/ping")
        assert "Content-Security-Policy" not in resp.headers


# --------------------------------------------------------------------------- #
# Rate-limit middleware
# --------------------------------------------------------------------------- #
class TestRateLimitMiddleware:
    def test_disabled_allows_unlimited_requests(self):
        from app.core.core_middleware.http_security_middleware import register_rate_limit_middleware

        app = _simple_app()
        register_rate_limit_middleware(app, enabled=False, max_requests=1, window_seconds=60)
        client = TestClient(app)
        for _ in range(5):
            assert client.get("/ping").status_code == 200

    def test_enabled_allows_requests_within_limit(self):
        from app.core.core_middleware.http_security_middleware import register_rate_limit_middleware

        app = _simple_app()
        register_rate_limit_middleware(app, enabled=True, max_requests=5, window_seconds=60)
        client = TestClient(app)
        for _ in range(5):
            assert client.get("/ping").status_code == 200

    def test_enabled_blocks_after_limit_exceeded(self):
        from app.core.core_middleware.http_security_middleware import register_rate_limit_middleware

        app = _simple_app()
        register_rate_limit_middleware(app, enabled=True, max_requests=2, window_seconds=60)
        client = TestClient(app)
        client.get("/ping")
        client.get("/ping")
        response = client.get("/ping")
        assert response.status_code == 429
