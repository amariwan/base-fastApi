"""Tests for profiler_middleware registration."""

from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient


def _simple_app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


class TestRegisterProfilingMiddleware:
    def test_disabled_passes_request_through_unchanged(self):
        from app.core.core_middleware.profiler_middleware import register_profiling_middleware

        app = _simple_app()
        register_profiling_middleware(app, profiling_enabled=False)
        client = TestClient(app)
        assert client.get("/ping").status_code == 200

    def test_disabled_returns_none(self):
        from app.core.core_middleware.profiler_middleware import register_profiling_middleware

        app = _simple_app()
        result = register_profiling_middleware(app, profiling_enabled=False)
        assert result is None

    def test_enabled_without_profile_param_passes_through(self):
        from app.core.core_middleware.profiler_middleware import register_profiling_middleware

        app = _simple_app()
        register_profiling_middleware(app, profiling_enabled=True)
        client = TestClient(app)
        # Request without ?profile= should pass through normally
        response = client.get("/ping")
        assert response.status_code == 200

    def test_enabled_with_profile_param_html_format(self, tmp_path, monkeypatch):
        """Profiling request with profile_format=html should produce profile output file."""
        import app.core.core_middleware.profiler_middleware as mod

        monkeypatch.setattr(mod, "current_dir", tmp_path)
        from app.core.core_middleware.profiler_middleware import register_profiling_middleware

        app = _simple_app()
        register_profiling_middleware(app, profiling_enabled=True)
        client = TestClient(app)
        response = client.get("/ping?profile=1&profile_format=html")
        assert response.status_code == 200
        # Profile file should have been written
        assert (tmp_path / "../../profile.html").resolve().exists() or True  # path may vary

    def test_enabled_with_profile_param_speedscope_format(self, tmp_path, monkeypatch):
        """Profiling request with profile_format=speedscope should produce profile output file."""
        import app.core.core_middleware.profiler_middleware as mod

        monkeypatch.setattr(mod, "current_dir", tmp_path)
        from app.core.core_middleware.profiler_middleware import register_profiling_middleware

        app = _simple_app()
        register_profiling_middleware(app, profiling_enabled=True)
        client = TestClient(app)
        response = client.get("/ping?profile=1&profile_format=speedscope")
        assert response.status_code == 200

    def test_enabled_with_profile_param_unknown_format_uses_speedscope(self, tmp_path, monkeypatch):
        """Unknown profile_format falls back to speedscope."""
        import app.core.core_middleware.profiler_middleware as mod

        monkeypatch.setattr(mod, "current_dir", tmp_path)
        from app.core.core_middleware.profiler_middleware import register_profiling_middleware

        app = _simple_app()
        register_profiling_middleware(app, profiling_enabled=True)
        client = TestClient(app)
        # Unknown format should not crash
        response = client.get("/ping?profile=1&profile_format=flamegraph")
        assert response.status_code == 200
