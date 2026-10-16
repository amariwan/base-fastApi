"""Framework-light public models for inference providers and consumers."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from app.core.core_ai.contracts.capabilities import (
    Capability,
    CapabilitySupport,
    PrivacyRequirement,
    ProviderLocation,
)


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    location: ProviderLocation
    configured: bool
    available: bool | None = None
    availability_detail: str | None = None


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    provider_id: str
    model_id: str
    capabilities: Mapping[Capability, CapabilitySupport] = field(default_factory=dict)
    context_window: int | None = None
    max_output_tokens: int | None = None
    input_cost_per_million: Decimal | None = None
    output_cost_per_million: Decimal | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.provider_id, self.model_id)

    def capability(self, capability: Capability) -> CapabilitySupport:
        return self.capabilities.get(capability, CapabilitySupport.UNKNOWN)

    def supports(self, required: set[Capability] | frozenset[Capability]) -> bool:
        return all(self.capability(capability).is_supported for capability in required)


@dataclass(frozen=True, slots=True)
class GenerationParameters:
    temperature: float | None = None
    max_output_tokens: int | None = None
    seed: int | None = None
    retries: int = 1


@dataclass(frozen=True, slots=True)
class ExecutionLimits:
    request_limit: int = 3
    tool_calls_limit: int = 8
    input_tokens_limit: int | None = None
    output_tokens_limit: int | None = None
    total_tokens_limit: int | None = None


@dataclass(frozen=True, slots=True)
class AIRequest:
    prompt: str
    system_prompt: str | None = None
    instructions: str | None = None
    provider_id: str | None = None
    model_id: str | None = None
    required_capabilities: frozenset[Capability] = frozenset()
    privacy: PrivacyRequirement = PrivacyRequirement.LOCAL_ONLY
    allow_cloud_fallback: bool = False
    allowed_tools: frozenset[str] = frozenset()
    allowed_mcp_servers: frozenset[str] = frozenset()
    granted_tool_permissions: frozenset[str] = frozenset()
    approved_tools: frozenset[str] = frozenset()
    parameters: GenerationParameters = field(default_factory=GenerationParameters)
    limits: ExecutionLimits = field(default_factory=ExecutionLimits)

    def __post_init__(self) -> None:
        if not self.prompt.strip():
            raise ValueError("prompt must not be empty")


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    tool_calls: int = 0
    estimated_cost: Decimal | None = None


@dataclass(frozen=True, slots=True)
class AIResult[OutputT]:
    output: OutputT
    model: ModelDescriptor
    usage: Usage
