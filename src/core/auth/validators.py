from __future__ import annotations

"""JWT validation helpers."""

from typing import TypedDict

import jwt
from fastapi import HTTPException, status

from shared.types import JSONValue

from .keys import get_jwks_client
from .settings import AuthSettings, get_auth_settings


class JWTHeader(TypedDict, total=False):
    alg: str
    kid: str


Claims = dict[str, JSONValue]


def validate_jwt(token: str) -> Claims:
    """Validate and decode a JWT using the configured mode."""
    settings = get_auth_settings()
    header = _get_header(token)
    _guard_none_algorithm(header)
    kwargs = _build_decode_kwargs(settings)
    mode = settings.MODE.lower()
    if mode == "jwks":
        return _decode_with_jwks(token, header, kwargs)
    if mode == "hs":
        return _decode_with_hmac(token, settings, kwargs)
    raise HTTPException(status_code=500, detail="auth_mode_invalid")


def _get_header(token: str) -> JWTHeader:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_header") from exc
    return {
        "alg": str(header.get("alg", "")),
        "kid": str(header.get("kid", "")),
    }


def _guard_none_algorithm(header: JWTHeader) -> None:
    if header.get("alg", "").upper() == "NONE":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="alg_none_forbidden")


def _build_decode_kwargs(settings: AuthSettings) -> dict[str, object]:
    options = {
        "verify_signature": settings.VERIFY_SIGNATURE,
        "verify_exp": settings.VERIFY_EXP,
        "verify_iss": settings.VERIFY_ISS,
        "verify_aud": settings.VERIFY_AUD,
        "require": ["sub"],
    }
    kwargs: dict[str, object] = {
        "algorithms": [alg.upper() for alg in settings.ALGORITHMS],
        "options": options,
        "leeway": settings.CLOCK_SKEW_SECS,
    }
    if settings.VERIFY_ISS and settings.ISSUER:
        kwargs["issuer"] = settings.ISSUER
    if settings.VERIFY_AUD and settings.AUDIENCE:
        kwargs["audience"] = settings.AUDIENCE
    return kwargs


def _decode_with_jwks(token: str, header: JWTHeader, kwargs: dict[str, object]) -> Claims:
    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="kid_missing")
    try:
        jwk = get_jwks_client().get_signing_key(kid)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="jwks_unavailable") from exc
    return _decode(token, jwk.key, kwargs)


def _decode_with_hmac(token: str, settings: AuthSettings, kwargs: dict[str, object]) -> Claims:
    if not settings.HS_SECRET:
        raise HTTPException(status_code=500, detail="auth_hs_secret_missing")
    return _decode(token, settings.HS_SECRET.get_secret_value(), kwargs)


def _decode(token: str, key: object, kwargs: dict[str, object]) -> Claims:
    payload = jwt.decode(token, key, **kwargs)
    return {str(k): v for k, v in payload.items()}


__all__ = ["validate_jwt"]

