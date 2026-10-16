"""Model descriptor registry with explicit duplicate handling."""

from collections.abc import Iterable

from app.core.core_ai.contracts import AIConfigurationError, ModelDescriptor, ModelNotFoundError


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[tuple[str, str], ModelDescriptor] = {}

    def register(self, model: ModelDescriptor) -> None:
        if model.key in self._models:
            raise AIConfigurationError(f"Model '{model.provider_id}:{model.model_id}' is already registered")
        self._models[model.key] = model

    def get(self, provider_id: str, model_id: str) -> ModelDescriptor:
        try:
            return self._models[(provider_id, model_id)]
        except KeyError as exc:
            raise ModelNotFoundError(f"Model '{provider_id}:{model_id}' is not registered") from exc

    def list(self, provider_id: str | None = None) -> tuple[ModelDescriptor, ...]:
        values: Iterable[ModelDescriptor] = self._models.values()
        if provider_id is not None:
            values = (model for model in values if model.provider_id == provider_id)
        return tuple(values)
