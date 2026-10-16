"""Provider registry with explicit duplicate handling."""

from app.core.core_ai.contracts import AIConfigurationError
from app.core.core_ai.contracts.protocols import AIProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}

    def register(self, provider: AIProvider) -> None:
        provider_id = provider.descriptor.provider_id
        if provider_id in self._providers:
            raise AIConfigurationError(f"Provider '{provider_id}' is already registered")
        self._providers[provider_id] = provider

    def get(self, provider_id: str) -> AIProvider:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise AIConfigurationError(f"Provider '{provider_id}' is not registered") from exc

    def list(self) -> tuple[AIProvider, ...]:
        return tuple(self._providers.values())
