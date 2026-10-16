"""Embedding-backed knowledge retrieval."""

from collections.abc import Mapping

from app.core.core_ai.embeddings import EmbeddingService
from app.core.core_ai.knowledge.vector_store import SearchResult, VectorStore


class KnowledgeRetriever:
    def __init__(self, *, embeddings: EmbeddingService, store: VectorStore) -> None:
        self._embeddings = embeddings
        self._store = store

    async def retrieve(
        self,
        *,
        tenant_id: str,
        query: str,
        limit: int,
        metadata_filter: Mapping[str, str] | None = None,
    ) -> tuple[SearchResult, ...]:
        query_vector = await self._embeddings.embed_query(query)
        return await self._store.search(
            tenant_id=tenant_id,
            query_embedding=query_vector,
            limit=limit,
            metadata_filter=metadata_filter,
        )
