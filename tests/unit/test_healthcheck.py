from __future__ import annotations

from core.healthcheck.schemas import HealthConfig
from core.healthcheck.security import is_admin
from core.healthcheck.services import build_safe_health_config


def test_build_safe_health_config(monkeypatch) -> None:
    monkeypatch.setenv("TEST_MODE", "true")
    cfg = build_safe_health_config()
    assert isinstance(cfg, HealthConfig)
    assert cfg.app.test_mode is True
    assert cfg.db.port == int(monkeypatch.getenv("DB_PORT", "5432"))


def test_is_admin() -> None:
    assert is_admin(["ADMIN", "user"])
    assert not is_admin(["viewer"])
    assert not is_admin(None)

