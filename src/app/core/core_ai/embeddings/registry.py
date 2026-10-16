"""Embedding model registration."""

from app.core.core_ai.contracts import AIConfigurationError
from pydantic_ai.embeddings import EmbeddingModel


class EmbeddingRegistry:
    def __init__(self) -> None:
        self._models: dict[str, EmbeddingModel] = {}

    def register(self, model_id: str, model: EmbeddingModel) -> None:
        if model_id in self._models:
            raise AIConfigurationError(f"Embedding model '{model_id}' is already registered")
        self._models[model_id] = model

    def get(self, model_id: str) -> EmbeddingModel:
        try:
            return self._models[model_id]
        except KeyError as exc:
            raise AIConfigurationError(f"Embedding model '{model_id}' is not registered") from exc
