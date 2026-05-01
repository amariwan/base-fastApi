"""JWKS key provider backed by PyJWT's built-in PyJWKClient."""

from __future__ import annotations

import ssl
from functools import lru_cache

from jwt import PyJWKClient

from .settings import get_auth_settings


def _build_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if get_auth_settings().DISABLE_SSL_VERIFY:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    return ctx


@lru_cache(maxsize=1)
def _cached_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, ssl_context=_build_ssl_context())


def get_jwks_client() -> PyJWKClient:
    """Return the singleton JWKS client configured from AuthSettings."""
    settings = get_auth_settings()
    if not settings.JWKS_URL:
        raise RuntimeError("AUTH_JWKS_URL missing")
    return _cached_client(str(settings.JWKS_URL))


def reset_jwks_client() -> None:
    """Reset the cached JWKS client (used in tests)."""
    _cached_client.cache_clear()


__all__ = ["get_jwks_client", "reset_jwks_client"]
