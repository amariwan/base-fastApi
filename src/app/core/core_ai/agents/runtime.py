"""Reusable agent definitions and bounded execution over the Core AI client."""

from dataclasses import dataclass
from typing import Protocol

from app.core.core_ai.agents.registry import AgentRegistry
from app.core.core_ai.contracts import (
    AIRequest,
    AIResult,
    Capability,
    ExecutionLimits,
    PrivacyRequirement,
)


class TextInference(Protocol):
    async def generate(self, request: AIRequest) -> AIResult[str]: ...


@dataclass(frozen=True, slots=True)
class AgentRunContext:
    privacy: PrivacyRequirement = PrivacyRequirement.LOCAL_ONLY
    granted_tool_permissions: frozenset[str] = frozenset()
    approved_tools: frozenset[str] = frozenset()
    limits: ExecutionLimits = ExecutionLimits()


class AgentRuntime:
    def __init__(self, *, registry: AgentRegistry, inference: TextInference) -> None:
        self._registry = registry
        self._inference = inference

    async def run(self, agent_id: str, prompt: str, *, context: AgentRunContext) -> AIResult[str]:
        definition = self._registry.get(agent_id)
        capabilities = set(definition.required_capabilities)
        if definition.allowed_tools or definition.allowed_mcp_servers:
            capabilities.add(Capability.TOOL_CALLING)
        return await self._inference.generate(
            AIRequest(
                prompt=prompt,
                instructions=definition.instructions,
                provider_id=definition.provider_id,
                model_id=definition.model_id,
                required_capabilities=frozenset(capabilities),
                privacy=context.privacy,
                allowed_tools=definition.allowed_tools,
                allowed_mcp_servers=definition.allowed_mcp_servers,
                granted_tool_permissions=context.granted_tool_permissions,
                approved_tools=context.approved_tools,
                limits=context.limits,
            )
        )
