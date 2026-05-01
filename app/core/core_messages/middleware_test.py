from __future__ import annotations

import base64
import json

from app.core.core_messages.middleware import _extract_locale_from_authorization_header


def _make_token(payload: dict[str, object]) -> str:
    header = {"alg": "none", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"{header_b64}.{payload_b64}.sig"


def test_extract_locale_from_bearer_header_returns_locale() -> None:
    token = _make_token({"locale": "de"})
    header = f"Bearer {token}"
    assert _extract_locale_from_authorization_header(header) == "de"


def test_extract_locale_from_bearer_header_accepts_locale_tag() -> None:
    token = _make_token({"locale": "en-US"})
    header = f"Bearer {token}"
    assert _extract_locale_from_authorization_header(header) == "en-US"


def test_extract_locale_from_bearer_header_returns_none_for_invalid_input() -> None:
    assert _extract_locale_from_authorization_header(None) is None
    assert _extract_locale_from_authorization_header("Basic abc") is None
    assert _extract_locale_from_authorization_header("Bearer not-a-jwt") is None
