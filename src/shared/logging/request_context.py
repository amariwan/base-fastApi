from __future__ import annotations

"""Lightweight request id propagation via contextvars."""

from contextvars import ContextVar, Token

_REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str | None) -> Token[str | None]:
    """Store the current request id in the async context."""
    return _REQUEST_ID.set(request_id)


def get_request_id() -> str | None:
    """Return the current request id if one has been set."""
    return _REQUEST_ID.get()


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the previous request id."""
    _REQUEST_ID.reset(token)
