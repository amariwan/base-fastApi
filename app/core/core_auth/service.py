"""JWT Authentication Service with optional signature validation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import lru_cache
from typing import TypedDict

import jwt
from app.shared.types import JSONValue
from fastapi import HTTPException, status

from .keys import get_jwks_client
from .settings import AuthSettings, get_auth_settings

# Algorithms that use a symmetric key — forbidden in JWKS mode to prevent
# algorithm-confusion attacks (attacker signs with HS256 using the RSA public key as secret).
_HMAC_ALGORITHMS: frozenset[str] = frozenset({"HS256", "HS384", "HS512"})


class JWTHeader(TypedDict, total=False):
    alg: str
    kid: str
    typ: str


class DecodedToken(TypedDict):
    header: JWTHeader
    payload: dict[str, JSONValue]


class _JwtOptions(TypedDict, total=False):
    """Mirrors jwt.types.Options (total=False) so structural subtyping holds."""

    verify_signature: bool
    verify_exp: bool
    verify_iss: bool
    verify_aud: bool
    verify_nbf: bool
    verify_iat: bool
    verify_jti: bool
    verify_sub: bool
    strict_aud: bool
    enforce_minimum_key_length: bool
    require: list[str]


class _JwtKwargs(TypedDict, total=False):
    algorithms: list[str]
    options: _JwtOptions
    leeway: int
    issuer: str
    audience: str


def _try_jwt_decode(fn: Callable[[], Mapping[str, JSONValue]]) -> dict[str, JSONValue]:
    """Run *fn* and map all PyJWT exceptions to HTTP 401."""
    try:
        raw = fn()
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token_expired") from exc
    except jwt.ImmatureSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token_not_yet_valid") from exc
    except jwt.InvalidSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token_signature_invalid") from exc
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token_audience_invalid") from exc
    except jwt.InvalidIssuerError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token_issuer_invalid") from exc
    except jwt.InvalidAlgorithmError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token_algorithm_invalid") from exc
    except jwt.MissingRequiredClaimError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token_claim_missing") from exc
    except jwt.DecodeError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token_format_invalid") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from exc
    return dict(raw)


class JWTAuthService:
    """Service for JWT validation with configurable signature verification."""

    def __init__(self, settings: AuthSettings | None = None) -> None:
        self._settings = settings or get_auth_settings()

    def decode_token(self, token: str) -> DecodedToken:
        """Decode and optionally validate a JWT, returning header and payload."""
        if self._settings.VALIDATE_SIGNATURE:
            return self._decode_with_validation(token)
        return self._decode_without_validation(token)

    def _decode_without_validation(self, token: str) -> DecodedToken:
        try:
            unverified = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_header") from exc

        if str(unverified.get("alg", "")).upper() == "NONE":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="alg_none_forbidden")

        header: JWTHeader = {
            "alg": str(unverified.get("alg", "")),
            "kid": str(unverified.get("kid", "")),
            "typ": str(unverified.get("typ", "JWT")),
        }
        try:
            raw_payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_nbf": False,
                    "verify_iss": False,
                    "verify_aud": False,
                },
            )
        except jwt.DecodeError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token_format_invalid") from exc
        except (ValueError, KeyError) as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token_payload_invalid") from exc
        return DecodedToken(header=header, payload={str(k): v for k, v in raw_payload.items()})

    def _decode_with_validation(self, token: str) -> DecodedToken:
        header = self._validated_header(token)
        kwargs = self._build_decode_kwargs()
        mode = self._settings.MODE.lower()
        if mode == "jwks":
            payload = self._decode_with_jwks(token, kwargs)
        elif mode == "hs":
            payload = self._decode_with_hmac(token, kwargs)
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="auth_mode_invalid")
        return DecodedToken(header=header, payload=payload)

    def _validated_header(self, token: str) -> JWTHeader:
        try:
            raw = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_header") from exc
        header: JWTHeader = {
            "alg": str(raw.get("alg", "")),
            "kid": str(raw.get("kid", "")),
            "typ": str(raw.get("typ", "JWT")),
        }
        if header.get("alg", "").upper() == "NONE":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="alg_none_forbidden")
        return header

    def _build_decode_kwargs(self) -> _JwtKwargs:
        s = self._settings
        algorithms = [alg.upper() for alg in s.ALGORITHMS] or ["RS256"]
        if s.MODE.lower() == "jwks":
            # Strip all HMAC algorithms when using JWKS to prevent algorithm-confusion attacks.
            # An attacker could otherwise forge a token signed with HS256 using the RSA public key as secret.
            algorithms = [alg for alg in algorithms if alg not in _HMAC_ALGORITHMS] or ["RS256"]
        elif s.MODE.lower() == "hs" and not any(alg in _HMAC_ALGORITHMS for alg in algorithms):
            algorithms.append("HS256")
        options: _JwtOptions = {
            "verify_signature": s.VERIFY_SIGNATURE,
            "verify_exp": s.VERIFY_EXP,
            "verify_iss": s.VERIFY_ISS,
            "verify_aud": s.VERIFY_AUD,
            "verify_nbf": True,
            "require": ["sub", "iat", "exp", "roles"],
        }
        kwargs: _JwtKwargs = {
            "algorithms": algorithms,
            "options": options,
            "leeway": s.CLOCK_SKEW_SECS,
        }
        if s.VERIFY_ISS and s.ISSUER:
            kwargs["issuer"] = s.ISSUER
        if s.VERIFY_AUD and s.AUDIENCE:
            kwargs["audience"] = s.AUDIENCE
        return kwargs

    def _decode_with_jwks(self, token: str, kwargs: _JwtKwargs) -> dict[str, JSONValue]:
        try:
            signing_key = get_jwks_client().get_signing_key_from_jwt(token)
        except (jwt.PyJWKClientConnectionError, jwt.PyJWKSetError, RuntimeError) as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="jwks_unavailable") from exc
        return _try_jwt_decode(lambda: jwt.decode(token, signing_key.key, **kwargs))

    def _decode_with_hmac(self, token: str, kwargs: _JwtKwargs) -> dict[str, JSONValue]:
        if not self._settings.HS_SECRET:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="auth_hs_secret_missing")
        secret = self._settings.HS_SECRET.get_secret_value()
        return _try_jwt_decode(lambda: jwt.decode(token, secret, **kwargs))


# Use an lru_cache as a lazy singleton factory to avoid module-level globals
@lru_cache(maxsize=1)
def get_jwt_service() -> JWTAuthService:
    """Return a lazily-initialized JWTAuthService singleton."""
    return JWTAuthService()


def reset_jwt_service() -> None:
    """Reset the singleton instance (useful for testing)."""
    get_jwt_service.cache_clear()


__all__ = [
    "DecodedToken",
    "JWTAuthService",
    "JWTHeader",
    "get_jwt_service",
    "reset_jwt_service",
]
