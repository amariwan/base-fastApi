"""Tenant-aware knowledge ingestion and retrieval."""

from app.core.core_ai.knowledge.chunking import chunk_text
from app.core.core_ai.knowledge.ingestion import KnowledgeIngestor
from app.core.core_ai.knowledge.retrieval import KnowledgeRetriever
from app.core.core_ai.knowledge.vector_store import InMemoryVectorStore, SearchResult, VectorRecord, VectorStore

__all__ = [
    "InMemoryVectorStore",
    "KnowledgeIngestor",
    "KnowledgeRetriever",
    "SearchResult",
    "VectorRecord",
    "VectorStore",
    "chunk_text",
]
