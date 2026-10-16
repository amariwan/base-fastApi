"""Controlled PydanticAI tool registration and permission resolution."""

from dataclasses import dataclass
from typing import Any

from app.core.core_ai.agents.approvals import require_approval
from app.core.core_ai.agents.permissions import require_permissions
from app.core.core_ai.contracts import AIConfigurationError
from pydantic_ai import Tool


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    tool: Tool[Any]
    required_permissions: frozenset[str] = frozenset()
    category: str = "general"
    requires_approval: bool = False


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, registered: RegisteredTool) -> None:
        name = registered.tool.name
        if name in self._tools:
            raise AIConfigurationError(f"Tool '{name}' is already registered")
        self._tools[name] = registered

    def resolve(
        self,
        names: set[str] | frozenset[str],
        *,
        granted_permissions: frozenset[str],
        approved_tools: frozenset[str] = frozenset(),
    ) -> tuple[Tool[Any], ...]:
        resolved: list[Tool[Any]] = []
        for name in sorted(names):
            try:
                registered = self._tools[name]
            except KeyError as exc:
                raise AIConfigurationError(f"Tool '{name}' is not registered") from exc
            require_permissions(name, registered.required_permissions, granted_permissions)
            require_approval(name, required=registered.requires_approval, approved_tools=approved_tools)
            resolved.append(registered.tool)
        return tuple(resolved)
