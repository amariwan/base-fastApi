from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request

import pytest

from core.auth.keys import JWKSClient


class DummyResponse:
    def __init__(self, payload: dict, *, status: int = 200, headers: dict[str, str] | None = None):
        self.status = status
        self._payload = payload
        self._headers = headers or {}

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self._headers.get(name, default)

    def __enter__(self) -> DummyResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_jwks_client_fetches_and_caches_keys() -> None:
    response = DummyResponse(
        {"keys": [{"kid": "abc", "kty": "RSA", "e": "AQAB", "n": "xyz"}]},
        headers={"ETag": "etag-1", "Cache-Control": "max-age=120"},
    )

    calls: list[Request] = []

    def _fetcher(request: Request) -> DummyResponse:
        calls.append(request)
        return response

    client = JWKSClient("https://issuer/jwks", fetcher=_fetcher)
    key = client.get_signing_key("abc")
    assert key.key_type == "RSA"
    assert calls and calls[0].headers["Accept"] == "application/json"


def test_jwks_client_raises_when_fetch_fails() -> None:
    def _fetcher(_: Request) -> DummyResponse:
        raise URLError("boom")

    client = JWKSClient("https://issuer/jwks", fetcher=_fetcher)
    with pytest.raises(RuntimeError):
        client.get_signing_key("missing")


def test_parse_max_age_has_floor() -> None:
    assert JWKSClient._parse_max_age("max-age=30") == 60
    assert JWKSClient._parse_max_age("public, max-age=600") == 600
