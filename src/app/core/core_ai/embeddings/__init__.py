"""Embedding registry and bounded execution service."""

from app.core.core_ai.embeddings.registry import EmbeddingRegistry
from app.core.core_ai.embeddings.service import EmbeddingService

__all__ = ["EmbeddingRegistry", "EmbeddingService"]
