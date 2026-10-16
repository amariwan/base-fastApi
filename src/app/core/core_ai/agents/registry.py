"""Reusable agent definitions and registration."""

from dataclasses import dataclass

from app.core.core_ai.contracts import AIConfigurationError, Capability


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    agent_id: str
    instructions: str
    provider_id: str | None = None
    model_id: str | None = None
    required_capabilities: frozenset[Capability] = frozenset()
    allowed_tools: frozenset[str] = frozenset()
    allowed_mcp_servers: frozenset[str] = frozenset()


class AgentRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, AgentDefinition] = {}

    def register(self, definition: AgentDefinition) -> None:
        if not definition.agent_id.strip():
            raise AIConfigurationError("Agent identifiers must not be empty")
        if definition.agent_id in self._definitions:
            raise AIConfigurationError(f"Agent '{definition.agent_id}' is already registered")
        self._definitions[definition.agent_id] = definition

    def get(self, agent_id: str) -> AgentDefinition:
        try:
            return self._definitions[agent_id]
        except KeyError as exc:
            raise AIConfigurationError(f"Agent '{agent_id}' is not registered") from exc
