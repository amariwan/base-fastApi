"""Deterministic, capability-aware model routing without silent cloud fallback."""

from dataclasses import dataclass

from app.core.core_ai.contracts import (
    Capability,
    ModelDescriptor,
    ModelNotFoundError,
    PrivacyRequirement,
    ProviderLocation,
)
from app.core.core_ai.registry import ModelRegistry, ProviderRegistry


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    privacy: PrivacyRequirement = PrivacyRequirement.LOCAL_ONLY
    allow_cloud_fallback: bool = False
    provider_priorities: tuple[str, ...] = ()


class ModelRouter:
    def __init__(
        self,
        *,
        providers: ProviderRegistry,
        models: ModelRegistry,
        default_provider: str,
        default_model: str,
    ) -> None:
        self._providers = providers
        self._models = models
        self._default_provider = default_provider
        self._default_model = default_model

    def select(
        self,
        *,
        required_capabilities: set[Capability] | frozenset[Capability],
        provider_id: str | None = None,
        model_id: str | None = None,
        policy: RoutingPolicy | None = None,
    ) -> ModelDescriptor:
        selected_policy = policy or RoutingPolicy()
        target_provider = provider_id or self._default_provider
        target_model = model_id or (self._default_model if target_provider == self._default_provider else None)

        if target_model is not None:
            model = self._models.get(target_provider, target_model)
            if self._eligible(model, required_capabilities, selected_policy, explicit_provider=provider_id is not None):
                return model
            if provider_id is not None or model_id is not None or not selected_policy.allow_cloud_fallback:
                raise self._no_match(required_capabilities)

        if not selected_policy.allow_cloud_fallback:
            raise self._no_match(required_capabilities)

        priorities = selected_policy.provider_priorities or tuple(
            provider.descriptor.provider_id for provider in self._providers.list()
        )
        for candidate_provider in priorities:
            for model in self._models.list(candidate_provider):
                if self._eligible(model, required_capabilities, selected_policy, explicit_provider=False):
                    return model
        raise self._no_match(required_capabilities)

    def _eligible(
        self,
        model: ModelDescriptor,
        required_capabilities: set[Capability] | frozenset[Capability],
        policy: RoutingPolicy,
        *,
        explicit_provider: bool,
    ) -> bool:
        provider = self._providers.get(model.provider_id).descriptor
        if not provider.configured or provider.available is False:
            return False
        if provider.location is ProviderLocation.CLOUD:
            if policy.privacy is PrivacyRequirement.LOCAL_ONLY:
                return False
            if not explicit_provider and not policy.allow_cloud_fallback:
                return False
        return model.supports(required_capabilities)

    @staticmethod
    def _no_match(required: set[Capability] | frozenset[Capability]) -> ModelNotFoundError:
        capabilities = ", ".join(sorted(capability.value for capability in required)) or "none"
        return ModelNotFoundError(f"No available model satisfies required capabilities: {capabilities}")
