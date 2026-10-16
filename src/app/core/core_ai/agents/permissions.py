"""Trusted permission checks for agent tools."""

from app.core.core_ai.contracts import ToolPermissionDeniedError


def require_permissions(tool_name: str, required: frozenset[str], granted: frozenset[str]) -> None:
    missing = required - granted
    if missing:
        raise ToolPermissionDeniedError(f"Tool '{tool_name}' requires permissions: {', '.join(sorted(missing))}")
