from __future__ import annotations

"""JWKS client with simple caching and ETag support."""

# ruff: noqa: S310  # urllib usage guarded by HTTPS scheme checks

import json
import time
from collections.abc import Callable
from functools import lru_cache
from http.client import HTTPResponse
from urllib.error import URLError
from urllib.request import Request, urlopen  # noqa: S310 - allow HTTP(S) JWKS fetches

import jwt

from .settings import get_auth_settings

JWKSFetcher = Callable[[Request], HTTPResponse]


def _default_fetcher(request: Request) -> HTTPResponse:
    return urlopen(request)  # noqa: S310 - guarded by scheme checks


class JWKSClient:
    """Fetch and cache JWKS documents for token verification."""

    def __init__(self, url: str, *, fetcher: JWKSFetcher = _default_fetcher):
        self._url = url
        self._fetcher = fetcher
        self._keys: dict[str, dict[str, object]] = {}
        self._expires_at = 0.0
        self._etag: str | None = None

    def get_signing_key(self, kid: str) -> jwt.PyJWK:
        """Return the signing key for the provided key id."""
        if self._needs_refresh(kid):
            self._refresh()
        key_data = self._keys.get(kid)
        if key_data is None:
            raise RuntimeError("jwks_kid_not_found")
        return jwt.PyJWK.from_dict(key_data)

    def _needs_refresh(self, kid: str) -> bool:
        return time.time() >= self._expires_at or kid not in self._keys

    def _refresh(self) -> None:
        if not self._url.lower().startswith(("http://", "https://")):
            raise RuntimeError("jwks_invalid_scheme")
        request = Request(
            self._url,
            headers={"Accept": "application/json", **({"If-None-Match": self._etag} if self._etag else {})},
            method="GET",
        )
        try:
            with self._fetcher(request) as response:
                self._update_from_response(response)
        except (URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("jwks_fetch_failed") from exc

    def _update_from_response(self, response: HTTPResponse) -> None:
        if response.status == 304:
            self._expires_at = time.time() + 300
            return
        payload = json.loads(response.read().decode("utf-8"))
        keys = payload.get("keys", [])
        self._keys = {
            entry["kid"]: entry for entry in keys if isinstance(entry, dict) and entry.get("kid")
        }
        self._etag = response.getheader("ETag")
        cache_control = response.getheader("Cache-Control", "")
        self._expires_at = time.time() + self._parse_max_age(cache_control)

    @staticmethod
    def _parse_max_age(header: str) -> int:
        for raw_part in header.lower().split(","):
            segment = raw_part.strip()
            if segment.startswith("max-age="):
                try:
                    return max(60, int(segment.split("=", 1)[1]))
                except ValueError:
                    return 300
        return 300


@lru_cache(maxsize=1)
def _cached_client(url: str) -> JWKSClient:
    return JWKSClient(url)


def get_jwks_client() -> JWKSClient:
    """Return the singleton JWKS client configured from AuthSettings."""
    settings = get_auth_settings()
    if not settings.JWKS_URL:
        raise RuntimeError("AUTH_JWKS_URL missing")
    return _cached_client(str(settings.JWKS_URL))


def reset_jwks_client() -> None:
    """Reset the cached JWKS client (used in tests)."""
    _cached_client.cache_clear()


__all__ = ["JWKSClient", "get_jwks_client", "reset_jwks_client"]
