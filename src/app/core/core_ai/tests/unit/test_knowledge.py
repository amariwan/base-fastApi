# Ruff's repository test ignore glob does not match co-located src/app tests.
# ruff: noqa: S101

import pytest
from app.core.core_ai.embeddings import EmbeddingRegistry, EmbeddingService
from app.core.core_ai.knowledge import (
    InMemoryVectorStore,
    KnowledgeIngestor,
    KnowledgeRetriever,
    VectorRecord,
    chunk_text,
)
from app.core.core_ai.observability import exact_match_dataset
from pydantic_ai.embeddings import TestEmbeddingModel


@pytest.mark.asyncio
async def test_embedding_service_supports_single_and_batch_inputs() -> None:
    registry = EmbeddingRegistry()
    registry.register("test:embed", TestEmbeddingModel(dimensions=4))
    service = EmbeddingService(registry=registry, default_model="test:embed", max_batch_size=2, timeout_seconds=1)

    query = await service.embed_query("hello")
    documents = await service.embed_documents(["one", "two"])

    assert len(query) == 4
    assert len(documents) == 2
    assert all(len(vector) == 4 for vector in documents)
    with pytest.raises(ValueError, match="batch"):
        await service.embed_documents(["one", "two", "three"])


@pytest.mark.asyncio
async def test_vector_store_enforces_tenant_and_metadata_filters() -> None:
    store = InMemoryVectorStore()
    await store.upsert(
        [
            VectorRecord("a", "tenant-a", (1.0, 0.0), "alpha", {"kind": "policy"}),
            VectorRecord("b", "tenant-b", (1.0, 0.0), "private", {"kind": "policy"}),
            VectorRecord("c", "tenant-a", (0.0, 1.0), "beta", {"kind": "note"}),
        ]
    )

    results = await store.search(
        tenant_id="tenant-a",
        query_embedding=(1.0, 0.0),
        limit=5,
        metadata_filter={"kind": "policy"},
    )

    assert [result.record.record_id for result in results] == ["a"]
    assert all(result.record.tenant_id == "tenant-a" for result in results)


def test_chunking_is_deterministic_and_preserves_overlap() -> None:
    chunks = chunk_text("abcdefghij", chunk_size=6, overlap=2)

    assert chunks == ("abcdef", "efghij")
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("text", chunk_size=2, overlap=2)


@pytest.mark.asyncio
async def test_ingestion_and_retrieval_form_an_offline_rag_pipeline() -> None:
    registry = EmbeddingRegistry()
    registry.register("test:embed", TestEmbeddingModel(dimensions=8))
    embeddings = EmbeddingService(registry=registry, default_model="test:embed", max_batch_size=8, timeout_seconds=1)
    store = InMemoryVectorStore()
    ingestor = KnowledgeIngestor(embeddings=embeddings, store=store, chunk_size=30, overlap=5)
    retriever = KnowledgeRetriever(embeddings=embeddings, store=store)

    record_ids = await ingestor.ingest(
        tenant_id="tenant-a",
        document_id="doc-1",
        text="FastAPI applications use dependency injection for reusable platform capabilities.",
        metadata={"source": "guide"},
    )
    results = await retriever.retrieve(tenant_id="tenant-a", query="dependency injection", limit=2)

    assert record_ids
    assert results
    assert all(result.record.tenant_id == "tenant-a" for result in results)


def test_evaluation_dataset_uses_deterministic_exact_match() -> None:
    cases: list[tuple[str, str]] = [("one", "ONE"), ("two", "TWO")]
    dataset = exact_match_dataset(name="uppercase", cases=cases)

    def uppercase(value: str) -> str:
        return value.upper()

    report = dataset.evaluate_sync(uppercase, progress=False)

    assert len(report.cases) == 2
