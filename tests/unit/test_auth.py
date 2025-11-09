from __future__ import annotations

import base64
import json

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from hypothesis import given
from hypothesis import strategies as st

from core.auth.deps import get_current_user, get_optional_user, get_value_from_jwt, require_admin
from core.auth.models import UserClaims
from core.auth.roles import extract_roles
from core.auth.settings import reload_role_settings
from core.auth.utils import extract_str_values, has_any, strip_prefix
from core.auth.validators import validate_jwt


def test_extract_roles_from_mixed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROLE_PREFIX", "app_")
    reload_role_settings()
    payload = {
        "roles": ["APP_ADMIN", "APP_reader"],
        "realm_access": {"roles": ["APP_writer"]},
        "resource_access": {"svc": {"roles": ["APP_admin"]}},
        "custom": {"roles": ["APP_support"]},
    }
    assert extract_roles(payload) == ["admin", "reader", "writer", "support"]


@given(st.lists(st.text()))
def test_user_claims_normalizes_roles(role_inputs: list[str]) -> None:
    claims = UserClaims(sub="abc", roles=role_inputs)
    expected = [role.strip().lower() for role in role_inputs if role.strip()]
    deduped = list(dict.fromkeys(expected))
    assert claims.roles == deduped


@given(st.lists(st.one_of(st.text(), st.integers(), st.none())))
def test_extract_str_values_property(values: list[str | int | None]) -> None:
    result = extract_str_values(values)
    assert all(value.strip() for value in result)


def test_strip_prefix() -> None:
    assert strip_prefix("APP_USER", "APP_") == "USER"
    assert strip_prefix("USER", "APP_") == "USER"


def test_has_any() -> None:
    assert has_any(["admin", "user"], ["editor", "ADMIN"])
    assert not has_any(["viewer"], ["editor"])


def test_validate_jwt_hs_success(hs_token) -> None:
    token = hs_token({"email": "u@example.com"})
    payload = validate_jwt(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "u@example.com"


def test_validate_jwt_rejects_alg_none() -> None:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps({"sub": "user-123"}).encode()).rstrip(b"=").decode()
    token = f"{header}.{body}."
    with pytest.raises(HTTPException) as exc:
        validate_jwt(token)
    assert exc.value.status_code == 401


def test_validate_jwt_jwks(monkeypatch, hs_token) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwks")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://issuer/jwks")
    from core.auth.settings import reload_auth_settings

    reload_auth_settings()

    class DummyJWK:
        def __init__(self, key: str) -> None:
            self.key = key

    class DummyClient:
        def get_signing_key(self, kid: str) -> DummyJWK:
            assert kid == "kid1"
            return DummyJWK("dev-secret")

    monkeypatch.setattr("core.auth.validators.get_jwks_client", lambda: DummyClient())
    token = hs_token(headers={"kid": "kid1"})
    payload = validate_jwt(token)
    assert payload["sub"] == "user-123"


@pytest.mark.asyncio
async def test_get_current_user_requires_credentials(hs_token) -> None:
    with pytest.raises(HTTPException) as exc:
        await get_current_user(None)  # type: ignore[arg-type]
    assert exc.value.status_code == 401

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=hs_token())
    user = await get_current_user(creds)
    assert user.sub == "user-123"


@pytest.mark.asyncio
async def test_get_optional_user_returns_none_without_token() -> None:
    assert await get_optional_user(None) is None


@pytest.mark.asyncio
async def test_get_value_from_jwt(hs_token) -> None:
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=hs_token({"email": "me@example.com"}))
    value = await get_value_from_jwt("email", creds)
    assert value == "me@example.com"


@pytest.mark.asyncio
async def test_require_admin_denies_without_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROLE_ADMIN_ROLES", "root")
    reload_role_settings()
    user = UserClaims(sub="abc", roles=["viewer"])
    with pytest.raises(HTTPException) as exc:
        await require_admin()(user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_bypassed_when_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROLE_ACTIVE", "false")
    reload_role_settings()
    user = UserClaims(sub="abc", roles=[])
    result = await require_admin()(user)
    assert result.sub == "abc"
