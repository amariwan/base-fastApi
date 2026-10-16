"""Unified embedding model registry and bounded async service."""

import asyncio

from app.core.core_ai.contracts import AIProviderError, AIRequestTimeoutError
from app.core.core_ai.embeddings.registry import EmbeddingRegistry


class EmbeddingService:
    def __init__(
        self,
        *,
        registry: EmbeddingRegistry,
        default_model: str,
        max_batch_size: int,
        timeout_seconds: float,
    ) -> None:
        if max_batch_size < 1:
            raise ValueError("max_batch_size must be positive")
        self._registry = registry
        self._default_model = default_model
        self._max_batch_size = max_batch_size
        self._timeout_seconds = timeout_seconds

    async def embed_query(self, text: str, *, model_id: str | None = None) -> tuple[float, ...]:
        vectors = await self._embed([text], input_type="query", model_id=model_id)
        return vectors[0]

    async def embed_documents(self, texts: list[str], *, model_id: str | None = None) -> tuple[tuple[float, ...], ...]:
        return await self._embed(texts, input_type="document", model_id=model_id)

    async def _embed(
        self,
        texts: list[str],
        *,
        input_type: str,
        model_id: str | None,
    ) -> tuple[tuple[float, ...], ...]:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("embedding inputs must contain non-empty text")
        if len(texts) > self._max_batch_size:
            raise ValueError(f"embedding batch exceeds maximum size {self._max_batch_size}")
        model = self._registry.get(model_id or self._default_model)
        try:
            async with asyncio.timeout(self._timeout_seconds):
                result = await model.embed(texts, input_type=input_type)  # type: ignore[arg-type]
        except TimeoutError as exc:
            raise AIRequestTimeoutError("Embedding request timed out") from exc
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise AIProviderError("Embedding provider request failed") from exc
        vectors = tuple(tuple(float(value) for value in vector) for vector in result.embeddings)
        if len(vectors) != len(texts) or not vectors or any(not vector for vector in vectors):
            raise AIProviderError("Embedding provider returned an invalid batch")
        dimensions = len(vectors[0])
        if any(len(vector) != dimensions for vector in vectors):
            raise AIProviderError("Embedding provider returned inconsistent dimensions")
        return vectors
