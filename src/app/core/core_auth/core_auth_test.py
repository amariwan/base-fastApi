"""Tests for the core_auth JWT validation module.

Coverage targets:
- settings: ALGORITHMS default, CLOCK_SKEW_SECS parsing, ROLE_HIERARCHY field
- models: UserClaims normalization, groups field
- roles: extraction from all claim sources, deduplication, prefix stripping,
         parse_hierarchy, get_effective_roles, extract_groups
- service: valid RS256 decode, expired token, alg=none, invalid signature,
           algorithm-confusion (HMAC blocked in JWKS mode), HS mode
- validators: validate_jwt wrapper
- deps: get_current_user (missing header, valid token, bad token),
        require_roles (pass, 403, hierarchy expansion)
- acl: check_acl (owner/group/other precedence), require_acl_perm dependency
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from app.core.core_auth.acl import Perm, ResourceACL, check_acl, require_acl_perm
from app.core.core_auth.deps import get_current_user, require_roles
from app.core.core_auth.models import UserClaims
from app.core.core_auth.roles import extract_groups, extract_roles, get_effective_roles, parse_hierarchy
from app.core.core_auth.service import JWTAuthService
from app.core.core_auth.settings import AuthSettings, RoleSettings
from app.shared.types import JSONValue
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Shared RSA key pair (module-scoped — generated once per test run)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def rsa_public_key(rsa_key):
    return rsa_key.public_key()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ISSUER = "https://idp.example.com/"
_AUDIENCE = "test-client"


def _payload(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    base: dict[str, Any] = {
        "sub": "user-abc123",
        "iat": now,
        "exp": now + 3600,
        "iss": _ISSUER,
        "aud": _AUDIENCE,
        "jti": "tok-001",
        "roles": ["GRPS_Portal_Admin", "GRPS_Portal_User"],
        "email": "user@example.com",
        "name": "Test User",
        "preferred_username": "testuser",
    }
    base.update(overrides)
    return base


def _rs256_token(private_key: Any, payload: dict[str, Any], *, kid: str = "key-1") -> str:
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


def _hs256_token(secret: str, payload: dict[str, Any]) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


def _jwks_service(private_key: Any, **settings_overrides: Any) -> tuple[JWTAuthService, MagicMock]:
    """Return (service, mock_client) with public key injected via mocked JWKS."""
    public_key = private_key.public_key()
    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key

    settings = AuthSettings(
        MODE="jwks",
        VALIDATE_SIGNATURE=True,
        VERIFY_SIGNATURE=True,
        VERIFY_EXP=True,
        VERIFY_ISS=True,
        VERIFY_AUD=True,
        ISSUER=_ISSUER,
        AUDIENCE=_AUDIENCE,
        ALGORITHMS=["RS256"],
        CLOCK_SKEW_SECS=30,
        **settings_overrides,
    )
    return JWTAuthService(settings=settings), mock_client


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------


class TestAuthSettings:
    def test_default_algorithms_is_rs256_only(self) -> None:
        settings = AuthSettings()
        assert settings.ALGORITHMS == ["RS256"]
        assert "HS256" not in settings.ALGORITHMS

    def test_algorithms_normalized_to_uppercase(self) -> None:
        settings = AuthSettings(ALGORITHMS="rs256,es256")
        assert settings.ALGORITHMS == ["RS256", "ES256"]

    def test_clock_skew_secs_accepts_int_string(self) -> None:
        settings = AuthSettings(CLOCK_SKEW_SECS="45")
        assert settings.CLOCK_SKEW_SECS == 45

    def test_clock_skew_secs_defaults_to_60(self) -> None:
        settings = AuthSettings()
        assert settings.CLOCK_SKEW_SECS == 60

    def test_empty_algorithms_string_falls_back_to_rs256(self) -> None:
        settings = AuthSettings(ALGORITHMS="")
        assert settings.ALGORITHMS == ["RS256"]


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


class TestUserClaims:
    def test_sub_must_not_be_empty(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserClaims(sub="   ")

    def test_roles_are_deduplicated_and_lowercased(self) -> None:
        user = UserClaims(sub="x", roles=["Admin", "admin", "USER", "user"])
        assert user.roles == ["admin", "user"]

    def test_roles_empty_by_default(self) -> None:
        user = UserClaims(sub="x")
        assert user.roles == []

    def test_sub_is_stripped(self) -> None:
        user = UserClaims(sub="  uuid-1  ")
        assert user.sub == "uuid-1"


# ---------------------------------------------------------------------------
# roles
# ---------------------------------------------------------------------------


def _as_json(data: dict[str, Any]) -> dict[str, JSONValue]:
    """Upcast plain test dict to the JSONValue mapping expected by extract_roles."""
    return data


class TestExtractRoles:
    def test_top_level_roles_array(self) -> None:
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_roles(_as_json({"sub": "u", "roles": ["Admin", "User"]}))
        assert "admin" in result
        assert "user" in result

    def test_resource_access_roles_extracted(self) -> None:
        payload = _as_json({"sub": "u", "resource_access": {"my-client": {"roles": ["client-admin"]}}})
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_roles(payload)
        assert "client-admin" in result

    def test_realm_access_roles_extracted(self) -> None:
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_roles(_as_json({"sub": "u", "realm_access": {"roles": ["realm-viewer"]}}))
        assert "realm-viewer" in result

    def test_resource_access_roles_not_duplicated(self) -> None:
        """resource_access roles must not appear twice even though the generic
        nested scan would find them too if not skipped."""
        payload = _as_json({"sub": "u", "resource_access": {"proxy": {"roles": ["proxy-role"]}}})
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_roles(payload)
        assert result.count("proxy-role") == 1

    def test_prefix_stripped_from_roles(self) -> None:
        payload = _as_json({"sub": "u", "roles": ["GRPS_Portal_Admin", "GRPS_Portal_User"]})
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="GRPS_")):
            result = extract_roles(payload)
        assert "portal_admin" in result
        assert "portal_user" in result
        assert not any(r.startswith("grps_") for r in result)

    def test_deduplication_across_sources(self) -> None:
        payload = _as_json({"sub": "u", "roles": ["viewer"], "groups": ["viewer"]})
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_roles(payload)
        assert result.count("viewer") == 1

    def test_empty_payload_returns_empty_list(self) -> None:
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_roles(_as_json({"sub": "u"}))
        assert result == []


# ---------------------------------------------------------------------------
# service — security tests
# ---------------------------------------------------------------------------


class TestJWTAuthServiceValidation:
    def test_valid_rs256_token_decoded(self, rsa_key: Any) -> None:
        svc, mock_client = _jwks_service(rsa_key)
        token = _rs256_token(rsa_key, _payload())
        with patch("app.core.core_auth.service.get_jwks_client", return_value=mock_client):
            decoded = svc.decode_token(token)
        assert decoded["payload"]["sub"] == "user-abc123"

    def test_expired_token_raises_401(self, rsa_key: Any) -> None:
        svc, mock_client = _jwks_service(rsa_key)
        token = _rs256_token(rsa_key, _payload(exp=int(time.time()) - 3600))
        with patch("app.core.core_auth.service.get_jwks_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                svc.decode_token(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "token_expired"

    def test_invalid_signature_raises_401(self, rsa_key: Any) -> None:
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        svc, mock_client = _jwks_service(rsa_key)
        # Token signed with a *different* private key
        token = _rs256_token(other_key, _payload())
        with patch("app.core.core_auth.service.get_jwks_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                svc.decode_token(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "token_signature_invalid"

    def test_wrong_issuer_raises_401(self, rsa_key: Any) -> None:
        svc, mock_client = _jwks_service(rsa_key)
        token = _rs256_token(rsa_key, _payload(iss="https://evil.example.com/"))
        with patch("app.core.core_auth.service.get_jwks_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                svc.decode_token(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "token_issuer_invalid"

    def test_wrong_audience_raises_401(self, rsa_key: Any) -> None:
        svc, mock_client = _jwks_service(rsa_key)
        token = _rs256_token(rsa_key, _payload(aud="other-client"))
        with patch("app.core.core_auth.service.get_jwks_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                svc.decode_token(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "token_audience_invalid"


class TestAlgorithmConfusion:
    """Verify that the service is protected against algorithm-confusion attacks."""

    def test_alg_none_rejected_in_validation_mode(self, rsa_key: Any) -> None:
        """A token with alg=none must be rejected before any key lookup."""
        svc, mock_client = _jwks_service(rsa_key)
        # Craft a token whose header claims alg=none
        # PyJWT won't encode with alg=none — we build the raw header manually
        import base64
        import json

        header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(_payload()).encode()).rstrip(b"=").decode()
        none_token = f"{header}.{payload_b64}."

        with patch("app.core.core_auth.service.get_jwks_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                svc.decode_token(none_token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "alg_none_forbidden"

    def test_alg_none_rejected_in_no_validation_mode(self, rsa_key: Any) -> None:
        """alg=none must also be rejected when signature validation is disabled."""
        settings = AuthSettings(VALIDATE_SIGNATURE=False)
        svc = JWTAuthService(settings=settings)

        import base64
        import json

        header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(_payload()).encode()).rstrip(b"=").decode()
        none_token = f"{header}.{payload_b64}."

        with pytest.raises(HTTPException) as exc:
            svc.decode_token(none_token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "alg_none_forbidden"

    def test_hs256_token_rejected_in_jwks_mode(self, rsa_key: Any) -> None:
        """A HS256-signed token must be rejected when the service is in JWKS mode.

        An attacker might try an algorithm-confusion attack by presenting a token
        whose alg header claims HS256. The service must refuse it because HS256 is
        not permitted in JWKS mode, regardless of the signing secret used.
        """
        # Use a plain HMAC secret — modern PyJWT refuses PEM public keys as HMAC secrets,
        # so we craft the attack scenario with a random secret instead. The test goal is to
        # verify that the *algorithm filter* blocks HS256 in JWKS mode before key-lookup.
        svc, mock_client = _jwks_service(rsa_key)
        token = jwt.encode(_payload(), "a-random-hmac-secret-at-least-32-bytes!!", algorithm="HS256")

        with patch("app.core.core_auth.service.get_jwks_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                svc.decode_token(token)
        # Must be rejected — 401 (algorithm not allowed) or 503 are both acceptable;
        # a valid payload must never be returned.
        assert exc.value.status_code in {401, 503}

    def test_hs_mode_accepts_hs256_token(self) -> None:
        """HS mode must accept a correctly signed HS256 token."""
        secret = "super-secret-for-testing-only-must-be-32b"
        settings = AuthSettings(
            MODE="hs",
            VALIDATE_SIGNATURE=True,
            VERIFY_SIGNATURE=True,
            VERIFY_EXP=True,
            VERIFY_ISS=True,
            VERIFY_AUD=True,
            ISSUER=_ISSUER,
            AUDIENCE=_AUDIENCE,
            ALGORITHMS=["HS256"],
            HS_SECRET=secret,
            CLOCK_SKEW_SECS=30,
        )
        svc = JWTAuthService(settings=settings)
        token = _hs256_token(secret, _payload())
        decoded = svc.decode_token(token)
        assert decoded["payload"]["sub"] == "user-abc123"


class TestNoValidationMode:
    def test_valid_token_decoded_without_signature_check(self, rsa_key: Any) -> None:
        settings = AuthSettings(VALIDATE_SIGNATURE=False)
        svc = JWTAuthService(settings=settings)
        token = _rs256_token(rsa_key, _payload())
        decoded = svc.decode_token(token)
        assert decoded["payload"]["sub"] == "user-abc123"

    def test_garbage_token_raises_401(self) -> None:
        settings = AuthSettings(VALIDATE_SIGNATURE=False)
        svc = JWTAuthService(settings=settings)
        with pytest.raises(HTTPException) as exc:
            svc.decode_token("not.a.token")
        assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# deps
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    def _make_request(self, auth_header: str | None) -> MagicMock:
        request = MagicMock()
        request.headers = {"Authorization": auth_header} if auth_header else {}
        return request

    def _make_creds(self) -> MagicMock:
        creds = MagicMock()
        creds.credentials = "irrelevant"
        return creds

    def test_missing_header_raises_401(self) -> None:
        request = self._make_request(None)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_user(request, None))
        assert exc.value.status_code == 401

    def test_non_bearer_scheme_raises_401(self) -> None:
        request = self._make_request("Basic dXNlcjpwYXNz")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_user(request, self._make_creds()))
        assert exc.value.status_code == 401

    def test_valid_token_returns_user_claims(self, rsa_key: Any) -> None:
        token = _rs256_token(rsa_key, _payload())
        request = self._make_request(f"Bearer {token}")
        valid_payload = _payload()

        async def _run() -> UserClaims:
            with patch("app.core.core_auth.deps.validate_jwt", return_value=valid_payload):
                return await get_current_user(request, self._make_creds())

        user = asyncio.run(_run())
        assert user.sub == valid_payload["sub"]

    def test_invalid_jwt_raises_401(self) -> None:
        request = self._make_request("Bearer invalid.token.here")

        async def _run() -> None:
            with patch("app.core.core_auth.deps.validate_jwt", side_effect=HTTPException(401, "invalid_token")):
                await get_current_user(request, self._make_creds())

        with pytest.raises(HTTPException) as exc:
            asyncio.run(_run())
        assert exc.value.status_code == 401


class TestRequireRoles:
    def _user(self, roles: list[str]) -> UserClaims:
        return UserClaims(sub="u", roles=roles)

    def test_user_with_required_role_passes(self) -> None:
        role_settings = RoleSettings(ACTIVE=True, ADMIN_ROLES=["admin"])
        dep = require_roles(lambda _cfg: ["admin"])

        async def _run() -> UserClaims:
            with patch("app.core.core_auth.deps.get_role_settings", return_value=role_settings):
                return await dep(self._user(["admin"]))

        user = asyncio.run(_run())
        assert user.sub == "u"

    def test_user_without_required_role_raises_403(self) -> None:
        role_settings = RoleSettings(ACTIVE=True, ADMIN_ROLES=["admin"])
        dep = require_roles(lambda _cfg: ["admin"])

        async def _run() -> None:
            with patch("app.core.core_auth.deps.get_role_settings", return_value=role_settings):
                await dep(self._user(["viewer"]))

        with pytest.raises(HTTPException) as exc:
            asyncio.run(_run())
        assert exc.value.status_code == 403

    def test_roles_inactive_bypasses_check(self) -> None:
        role_settings = RoleSettings(ACTIVE=False)
        dep = require_roles(lambda _cfg: ["admin"])

        async def _run() -> UserClaims:
            with patch("app.core.core_auth.deps.get_role_settings", return_value=role_settings):
                return await dep(self._user([]))

        user = asyncio.run(_run())
        assert user.sub == "u"


# ---------------------------------------------------------------------------
# parse_hierarchy
# ---------------------------------------------------------------------------


class TestParseHierarchy:
    def test_linear_chain(self) -> None:
        h = parse_hierarchy("admin>editor>reader")
        assert h["admin"] == frozenset({"admin", "editor", "reader"})
        assert h["editor"] == frozenset({"editor", "reader"})
        assert h["reader"] == frozenset({"reader"})

    def test_peers_at_same_level(self) -> None:
        h = parse_hierarchy("admin>editor>reader,user")
        # admin inherits everything
        assert h["admin"] == frozenset({"admin", "editor", "reader", "user"})
        # editor inherits both peers at the bottom
        assert h["editor"] == frozenset({"editor", "reader", "user"})
        # peers do NOT inherit each other
        assert h["reader"] == frozenset({"reader"})
        assert h["user"] == frozenset({"user"})

    def test_multiple_peers_at_top(self) -> None:
        # Peers at the same level do NOT inherit each other (only inherit levels below).
        h = parse_hierarchy("superadmin,admin>editor>reader")
        assert h["superadmin"] == frozenset({"superadmin", "editor", "reader"})
        assert h["admin"] == frozenset({"admin", "editor", "reader"})
        assert h["editor"] == frozenset({"editor", "reader"})
        assert h["reader"] == frozenset({"reader"})

    def test_normalized_to_lowercase(self) -> None:
        h = parse_hierarchy("Admin>Editor>Reader")
        assert "admin" in h
        assert "editor" in h
        assert "reader" in h

    def test_whitespace_ignored(self) -> None:
        h = parse_hierarchy(" admin > editor > reader ")
        assert "admin" in h

    def test_empty_string_returns_empty_dict(self) -> None:
        assert parse_hierarchy("") == {}

    def test_single_role(self) -> None:
        h = parse_hierarchy("admin")
        assert h["admin"] == frozenset({"admin"})


# ---------------------------------------------------------------------------
# get_effective_roles
# ---------------------------------------------------------------------------


class TestGetEffectiveRoles:
    def test_no_hierarchy_returns_original_roles(self) -> None:
        cfg = RoleSettings(HIERARCHY=None)
        result = get_effective_roles(["editor", "reader"], cfg)
        assert result == {"editor", "reader"}

    def test_admin_inherits_all(self) -> None:
        cfg = RoleSettings(HIERARCHY="admin>editor>reader,user")
        result = get_effective_roles(["admin"], cfg)
        assert result == {"admin", "editor", "reader", "user"}

    def test_editor_inherits_below(self) -> None:
        cfg = RoleSettings(HIERARCHY="admin>editor>reader,user")
        result = get_effective_roles(["editor"], cfg)
        assert result == {"editor", "reader", "user"}

    def test_reader_inherits_nothing(self) -> None:
        cfg = RoleSettings(HIERARCHY="admin>editor>reader,user")
        result = get_effective_roles(["reader"], cfg)
        assert result == {"reader"}

    def test_role_not_in_hierarchy_kept_as_is(self) -> None:
        cfg = RoleSettings(HIERARCHY="admin>editor")
        result = get_effective_roles(["viewer"], cfg)
        assert result == {"viewer"}

    def test_multiple_user_roles_merged(self) -> None:
        cfg = RoleSettings(HIERARCHY="admin>editor>reader")
        # user holds both editor and reader: effective should be their union
        result = get_effective_roles(["editor", "reader"], cfg)
        assert result == {"editor", "reader"}

    def test_expansion_does_not_mutate_user_claims(self) -> None:
        cfg = RoleSettings(HIERARCHY="admin>editor>reader")
        original = ["admin"]
        get_effective_roles(original, cfg)
        assert original == ["admin"]  # UserClaims.roles unchanged


# ---------------------------------------------------------------------------
# require_roles with hierarchy
# ---------------------------------------------------------------------------


class TestRequireRolesWithHierarchy:
    def _user(self, roles: list[str]) -> UserClaims:
        return UserClaims(sub="u", roles=roles)

    def test_editor_inherits_read_permission(self) -> None:
        """An editor should pass a require_read guard via hierarchy expansion."""
        cfg = RoleSettings(
            ACTIVE=True,
            HIERARCHY="admin>editor>reader",
            READ_ROLES=["reader"],
            WRITE_ROLES=["editor"],
            ADMIN_ROLES=["admin"],
        )
        dep = require_roles(lambda c: c.READ_ROLES)

        async def _run() -> UserClaims:
            with patch("app.core.core_auth.deps.get_role_settings", return_value=cfg):
                return await dep(self._user(["editor"]))

        user = asyncio.run(_run())
        assert user.sub == "u"

    def test_admin_inherits_all_permissions(self) -> None:
        cfg = RoleSettings(
            ACTIVE=True,
            HIERARCHY="admin>editor>reader",
            READ_ROLES=["reader"],
            WRITE_ROLES=["editor"],
            ADMIN_ROLES=["admin"],
        )
        dep = require_roles(lambda c: c.READ_ROLES)

        async def _run() -> UserClaims:
            with patch("app.core.core_auth.deps.get_role_settings", return_value=cfg):
                return await dep(self._user(["admin"]))

        asyncio.run(_run())  # must not raise

    def test_reader_cannot_write(self) -> None:
        cfg = RoleSettings(
            ACTIVE=True,
            HIERARCHY="admin>editor>reader",
            WRITE_ROLES=["editor"],
            ADMIN_ROLES=["admin"],
        )
        dep = require_roles(lambda c: c.WRITE_ROLES)

        async def _run() -> None:
            with patch("app.core.core_auth.deps.get_role_settings", return_value=cfg):
                await dep(self._user(["reader"]))

        with pytest.raises(HTTPException) as exc:
            asyncio.run(_run())
        assert exc.value.status_code == 403

    def test_keycloak_style_with_prefix(self) -> None:
        """Simulate real Keycloak token: GRPS_Portal_DocuFlow_Admin → admin after prefix strip."""
        cfg = RoleSettings(
            ACTIVE=True,
            PREFIX="GRPS_Portal_DocuFlow_",
            HIERARCHY="admin>fachgroup>legal",
            READ_ROLES=["legal"],
            WRITE_ROLES=["fachgroup"],
            ADMIN_ROLES=["admin"],
        )
        # After prefix stripping by extract_roles, the role becomes "admin"
        dep = require_roles(lambda c: c.READ_ROLES)

        async def _run() -> UserClaims:
            with patch("app.core.core_auth.deps.get_role_settings", return_value=cfg):
                # Simulate a user whose token contained GRPS_Portal_DocuFlow_FachGroup
                # → after prefix stripping in UserClaims: ["fachgroup"]
                return await dep(self._user(["fachgroup"]))

        user = asyncio.run(_run())
        assert user.sub == "u"  # fachgroup inherits legal → passes require_read


# ---------------------------------------------------------------------------
# models — groups field
# ---------------------------------------------------------------------------


class TestUserClaimsGroups:
    def test_groups_empty_by_default(self) -> None:
        user = UserClaims(sub="x")
        assert user.groups == []

    def test_groups_deduplicated_and_lowercased(self) -> None:
        user = UserClaims(sub="x", groups=["Editors", "EDITORS", "viewers"])
        assert user.groups == ["editors", "viewers"]

    def test_groups_whitespace_stripped(self) -> None:
        user = UserClaims(sub="x", groups=["  admins  "])
        assert user.groups == ["admins"]

    def test_groups_and_roles_are_independent(self) -> None:
        user = UserClaims(sub="x", roles=["editor"], groups=["editors"])
        assert user.roles == ["editor"]
        assert user.groups == ["editors"]


# ---------------------------------------------------------------------------
# roles — extract_groups
# ---------------------------------------------------------------------------


class TestExtractGroups:
    def test_top_level_groups_extracted(self) -> None:
        payload = _as_json({"sub": "u", "groups": ["admins", "viewers"]})
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_groups(payload)
        assert result == ["admins", "viewers"]

    def test_groups_lowercased(self) -> None:
        payload = _as_json({"sub": "u", "groups": ["Admins", "VIEWERS"]})
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_groups(payload)
        assert result == ["admins", "viewers"]

    def test_groups_deduplicated(self) -> None:
        payload = _as_json({"sub": "u", "groups": ["editors", "Editors", "EDITORS"]})
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_groups(payload)
        assert result == ["editors"]

    def test_prefix_stripped_from_groups(self) -> None:
        payload = _as_json({"sub": "u", "groups": ["GRPS_Portal_DocuFlow_FachGroup"]})
        with patch(
            "app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="GRPS_Portal_DocuFlow_")
        ):
            result = extract_groups(payload)
        assert result == ["fachgroup"]

    def test_missing_groups_claim_returns_empty(self) -> None:
        payload = _as_json({"sub": "u", "roles": ["admin"]})
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_groups(payload)
        assert result == []

    def test_groups_independent_from_roles(self) -> None:
        """extract_groups must not return role-only values."""
        payload = _as_json({"sub": "u", "roles": ["admin"], "groups": ["editors"]})
        with patch("app.core.core_auth.roles.get_role_settings", return_value=RoleSettings(PREFIX="")):
            result = extract_groups(payload)
        assert result == ["editors"]
        assert "admin" not in result


# ---------------------------------------------------------------------------
# acl — check_acl (the core logic)
# ---------------------------------------------------------------------------


class TestCheckACL:
    def _user(self, sub: str, groups: list[str] | None = None) -> UserClaims:
        return UserClaims(sub=sub, groups=groups or [])

    def _resource(
        self,
        owner_id: str,
        group_id: str | None = None,
        owner_perm: Perm = Perm.RWD,
        group_perm: Perm = Perm.RW,
        other_perm: Perm = Perm.READ,
    ) -> ResourceACL:
        return ResourceACL(
            owner_id=owner_id,
            group_id=group_id,
            owner_perm=owner_perm,
            group_perm=group_perm,
            other_perm=other_perm,
        )

    # --- owner path ---

    def test_owner_has_rwd_by_default(self) -> None:
        user = self._user("alice")
        resource = self._resource("alice")
        assert check_acl(user, resource, Perm.READ)
        assert check_acl(user, resource, Perm.WRITE)
        assert check_acl(user, resource, Perm.DELETE)

    def test_owner_limited_to_owner_perm(self) -> None:
        user = self._user("alice")
        resource = self._resource("alice", owner_perm=Perm.READ)
        assert check_acl(user, resource, Perm.READ)
        assert not check_acl(user, resource, Perm.WRITE)
        assert not check_acl(user, resource, Perm.DELETE)

    def test_owner_takes_precedence_over_group(self) -> None:
        """Even when the owner is also in the resource group, owner_perm wins."""
        user = self._user("alice", groups=["editors"])
        resource = self._resource(
            "alice",
            group_id="editors",
            owner_perm=Perm.READ,  # owner restricted
            group_perm=Perm.RWD,  # group has more
        )
        assert check_acl(user, resource, Perm.READ)
        assert not check_acl(user, resource, Perm.WRITE)

    # --- group path ---

    def test_group_member_respects_group_perm(self) -> None:
        user = self._user("bob", groups=["editors"])
        resource = self._resource("alice", group_id="editors", group_perm=Perm.RW)
        assert check_acl(user, resource, Perm.READ)
        assert check_acl(user, resource, Perm.WRITE)
        assert not check_acl(user, resource, Perm.DELETE)

    def test_group_match_is_case_insensitive(self) -> None:
        """Groups in UserClaims are lowercased; resource group_id comparison must match."""
        user = self._user("bob", groups=["editors"])  # already normalised
        resource = self._resource("alice", group_id="Editors", group_perm=Perm.RW)
        assert check_acl(user, resource, Perm.READ)

    def test_non_member_does_not_get_group_perm(self) -> None:
        user = self._user("bob", groups=["viewers"])
        resource = self._resource("alice", group_id="editors", group_perm=Perm.RWD, other_perm=Perm.READ)
        # bob is not in editors → falls through to other_perm
        assert check_acl(user, resource, Perm.READ)
        assert not check_acl(user, resource, Perm.WRITE)

    def test_no_group_skips_group_check(self) -> None:
        """When group_id is None the group path must be skipped entirely."""
        user = self._user("bob", groups=["editors"])
        resource = self._resource("alice", group_id=None, other_perm=Perm.READ)
        assert check_acl(user, resource, Perm.READ)
        assert not check_acl(user, resource, Perm.WRITE)

    # --- other path ---

    def test_other_user_respects_other_perm(self) -> None:
        user = self._user("charlie")
        resource = self._resource("alice", group_id="editors", other_perm=Perm.READ)
        assert check_acl(user, resource, Perm.READ)
        assert not check_acl(user, resource, Perm.WRITE)

    def test_other_deny_all(self) -> None:
        user = self._user("charlie")
        resource = self._resource("alice", other_perm=Perm(0))
        assert not check_acl(user, resource, Perm.READ)

    # --- composite permissions ---

    def test_composite_perm_requires_all_bits(self) -> None:
        """Perm.RW means the user must hold both READ and WRITE."""
        user = self._user("bob", groups=["viewers"])
        resource = self._resource("alice", group_id="viewers", group_perm=Perm.READ)
        # READ granted but not WRITE → Perm.RW denied
        assert check_acl(user, resource, Perm.READ)
        assert not check_acl(user, resource, Perm.RW)

    def test_perm_none_always_passes(self) -> None:
        """Requiring Perm(0) (no permissions) is always approved."""
        user = self._user("charlie")
        resource = self._resource("alice", other_perm=Perm(0))
        assert check_acl(user, resource, Perm(0))

    # --- Linux 644 defaults ---

    def test_default_perms_mirror_linux_644(self) -> None:
        """Default ResourceACL (owner=RW, group=R, other=R) matches Linux 644."""
        owner = self._user("alice")
        member = self._user("bob", groups=["staff"])
        other = self._user("charlie")
        resource = ResourceACL(owner_id="alice", group_id="staff")

        # owner: rw
        assert check_acl(owner, resource, Perm.RW)
        assert not check_acl(owner, resource, Perm.DELETE)
        # group: r
        assert check_acl(member, resource, Perm.READ)
        assert not check_acl(member, resource, Perm.WRITE)
        # other: r
        assert check_acl(other, resource, Perm.READ)
        assert not check_acl(other, resource, Perm.WRITE)


# ---------------------------------------------------------------------------
# acl — require_acl_perm FastAPI dependency
# ---------------------------------------------------------------------------


class TestRequireACLPerm:
    def _user(self, sub: str, groups: list[str] | None = None) -> UserClaims:
        return UserClaims(sub=sub, groups=groups or [])

    def _resource(self, owner_id: str, **kwargs: Any) -> ResourceACL:
        return ResourceACL(owner_id=owner_id, **kwargs)

    def test_owner_passes(self) -> None:
        user = self._user("alice")
        resource = self._resource("alice", owner_perm=Perm.RWD)
        dep = require_acl_perm(lambda: resource, Perm.WRITE)

        async def _run() -> UserClaims:
            return await dep(user, resource)

        result: UserClaims = asyncio.run(_run())
        assert result.sub == "alice"

    def test_group_member_passes(self) -> None:
        user = self._user("bob", groups=["editors"])
        resource = self._resource("alice", group_id="editors", group_perm=Perm.RW)
        dep = require_acl_perm(lambda: resource, Perm.WRITE)

        async def _run() -> UserClaims:
            return await dep(user, resource)

        result: UserClaims = asyncio.run(_run())
        assert result.sub == "bob"

    def test_other_denied_write_raises_403(self) -> None:
        user = self._user("charlie")
        resource = self._resource("alice", other_perm=Perm.READ)
        dep = require_acl_perm(lambda: resource, Perm.WRITE)

        async def _run() -> None:
            await dep(user, resource)

        with pytest.raises(HTTPException) as exc:
            asyncio.run(_run())
        assert exc.value.status_code == 403

    def test_403_body_contains_required_perm(self) -> None:
        user = self._user("charlie")
        resource = self._resource("alice", other_perm=Perm.READ)
        dep = require_acl_perm(lambda: resource, Perm.DELETE, detail="Cannot delete")

        async def _run() -> None:
            await dep(user, resource)

        with pytest.raises(HTTPException) as exc:
            asyncio.run(_run())
        body = exc.value.detail
        assert isinstance(body, dict)
        assert body["detail"] == "Cannot delete"
        assert "required_perm" in body

    def test_owner_denied_when_owner_perm_insufficient(self) -> None:
        user = self._user("alice")
        resource = self._resource("alice", owner_perm=Perm.READ)
        dep = require_acl_perm(lambda: resource, Perm.DELETE)

        async def _run() -> None:
            await dep(user, resource)

        with pytest.raises(HTTPException) as exc:
            asyncio.run(_run())
        assert exc.value.status_code == 403

    def test_perm_none_always_passes(self) -> None:
        """A dependency requiring Perm(0) must never deny anyone."""
        user = self._user("charlie")
        resource = self._resource("alice", other_perm=Perm(0))
        dep = require_acl_perm(lambda: resource, Perm(0))

        async def _run() -> UserClaims:
            return await dep(user, resource)

        result: UserClaims = asyncio.run(_run())
        assert result.sub == "charlie"
