from __future__ import annotations

import os
from collections.abc import Callable, Iterator

import jwt
import pytest

from config import reset_settings_cache
from core.auth.keys import reset_jwks_client
from core.auth.settings import reload_auth_settings, reload_role_settings

BASE_ENV = {
    "APP_ENV": "test",
    "APP_NAME": "service",
    "API_PREFIX": "/api",
    "API_VERSION": "v1",
    "TEST_MODE": "false",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_USERNAME": "user",
    "DB_PASSWORD": "pass",
    "DB_DATABASE": "db",
    "DB_POOL_SIZE": "5",
    "DB_MAX_OVERFLOW": "5",
    "DB_SSL": "false",
    "AUTH_MODE": "hs",
    "AUTH_HS_SECRET": "dev-secret",
    "ROLE_ACTIVE": "true",
    "ROLE_READ_ROLES": "[]",
    "ROLE_WRITE_ROLES": "[]",
    "ROLE_DELETE_ROLES": "[]",
    "ROLE_ADMIN_ROLES": '["admin"]',
}


@pytest.fixture(autouse=True)
def _base_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)
    reset_settings_cache()
    reload_auth_settings()
    reload_role_settings()
    reset_jwks_client()
    yield
    reset_settings_cache()
    reset_jwks_client()


@pytest.fixture
def hs_token(monkeypatch: pytest.MonkeyPatch) -> Callable[..., str]:
    secret = os.getenv("AUTH_HS_SECRET", "dev-secret")

    def _build(
        payload: dict[str, object] | None = None,
        *,
        headers: dict[str, str] | None = None,
        **claims: object,
    ) -> str:
        body = {"sub": "user-123", **(payload or {}), **claims}
        return jwt.encode(body, secret, algorithm="HS256", headers=headers)

    return _build
