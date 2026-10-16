"""PydanticAI model-provider adapters. Construction performs no network I/O."""

from collections.abc import Callable

from app.core.core_ai.contracts import AIConfigurationError, ModelDescriptor, ProviderDescriptor
from pydantic_ai.models import Model


class PydanticAIProvider:
    def __init__(self, descriptor: ProviderDescriptor, factory: Callable[[str], Model] | None) -> None:
        self._descriptor = descriptor
        self._factory = factory

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    def build_model(self, model_id: str) -> Model:
        if not self._descriptor.configured or self._factory is None:
            raise AIConfigurationError(f"Provider '{self._descriptor.provider_id}' is not configured")
        return self._factory(model_id)

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        # Most providers do not expose a portable, authoritative model-list API.
        return ()
