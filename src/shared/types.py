from __future__ import annotations

"""Shared foundational typing helpers used across the service."""

JSONPrimitive = str | int | float | bool | None
JSONValue = JSONPrimitive | dict[str, "JSONValue"] | list["JSONValue"]

__all__ = ["JSONPrimitive", "JSONValue"]
