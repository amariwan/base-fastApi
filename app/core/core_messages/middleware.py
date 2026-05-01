from __future__ import annotations

import base64
import json
from collections.abc import Awaitable, Callable
from typing import cast

from app.shared.types import JSONValue
from fastapi import FastAPI, Request
from starlette.responses import Response

from . import reset_request_message_language, set_request_message_language


def _decode_jwt_payload_without_verification(token: str) -> dict[str, JSONValue] | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None

    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode((payload + padding).encode("utf-8"))
        parsed: object = json.loads(decoded.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None

    return cast(dict[str, JSONValue], parsed) if isinstance(parsed, dict) else None


def _extract_locale_from_authorization_header(header_value: str | None) -> str | None:
    if not header_value:
        return None
    scheme, _, value = header_value.strip().partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None

    payload = _decode_jwt_payload_without_verification(value.strip())
    if not payload:
        return None

    locale = payload.get("locale")
    return locale.strip() if isinstance(locale, str) and locale.strip() else None


def register_message_language_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def message_language_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        token = set_request_message_language(
            _extract_locale_from_authorization_header(request.headers.get("Authorization"))
        )
        try:
            return await call_next(request)
        finally:
            reset_request_message_language(token)


__all__ = ["register_message_language_middleware"]
