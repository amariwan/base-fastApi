from __future__ import annotations

from config import (
    AppSettings,
    DbSettings,
    LogLevel,
    get_app_settings,
    get_db_settings,
    get_role_settings,
    reset_settings_cache,
)


def test_app_settings_allowed_hosts(monkeypatch) -> None:
    monkeypatch.setenv("ALLOWED_HOSTS", "example.com,foo")
    reset_settings_cache("app")
    app_settings = get_app_settings()
    assert isinstance(app_settings, AppSettings)
    assert app_settings.allowed_hosts_list == ["example.com", "foo"]
    assert app_settings.LOG_LEVEL in LogLevel


def test_role_settings_properties(monkeypatch) -> None:
    monkeypatch.setenv("ROLE_READ_ROLES", "reader,user")
    reset_settings_cache("roles")
    role_settings = get_role_settings()
    assert role_settings.read_roles == ["reader", "user"]


def test_db_settings_singleton(monkeypatch) -> None:
    monkeypatch.setenv("DB_DATABASE", "db2")
    reset_settings_cache("db")
    db_settings = get_db_settings()
    assert isinstance(db_settings, DbSettings)
    assert db_settings.DB_DATABASE == "db2"
