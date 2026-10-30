"""Shared JSON value contract for infrastructure adapters."""

from __future__ import annotations

JSONValue = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]

__all__ = ["JSONValue"]
