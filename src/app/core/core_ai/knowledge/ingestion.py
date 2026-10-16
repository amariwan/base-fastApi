"""Deterministic document ingestion into a vector store."""

import hashlib
from collections.abc import Mapping

from app.core.core_ai.embeddings import EmbeddingService
from app.core.core_ai.knowledge.chunking import chunk_text
from app.core.core_ai.knowledge.vector_store import VectorRecord, VectorStore


class KnowledgeIngestor:
    def __init__(self, *, embeddings: EmbeddingService, store: VectorStore, chunk_size: int, overlap: int) -> None:
        self._embeddings = embeddings
        self._store = store
        self._chunk_size = chunk_size
        self._overlap = overlap

    async def ingest(
        self,
        *,
        tenant_id: str,
        document_id: str,
        text: str,
        metadata: Mapping[str, str] | None = None,
    ) -> tuple[str, ...]:
        if not tenant_id or not document_id:
            raise ValueError("tenant_id and document_id are required")
        chunks = chunk_text(text, chunk_size=self._chunk_size, overlap=self._overlap)
        if not chunks:
            return ()
        vectors = await self._embeddings.embed_documents(list(chunks))
        record_ids = tuple(_chunk_id(document_id, index, chunk) for index, chunk in enumerate(chunks))
        records = [
            VectorRecord(
                record_id=record_id,
                tenant_id=tenant_id,
                embedding=vector,
                text=chunk,
                metadata={**(metadata or {}), "document_id": document_id, "chunk_index": str(index)},
            )
            for index, (record_id, chunk, vector) in enumerate(zip(record_ids, chunks, vectors, strict=True))
        ]
        await self._store.upsert(records)
        return record_ids


def _chunk_id(document_id: str, index: int, text: str) -> str:
    digest = hashlib.sha256(f"{document_id}:{index}:{text}".encode()).hexdigest()[:24]
    return f"{document_id}:{index}:{digest}"
