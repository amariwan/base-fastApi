"""Tenant-aware vector-store port and process-local adapter."""

import asyncio
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VectorRecord:
    record_id: str
    tenant_id: str
    embedding: tuple[float, ...]
    text: str
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchResult:
    record: VectorRecord
    score: float


class VectorStore(Protocol):
    async def upsert(self, records: Sequence[VectorRecord]) -> None: ...

    async def search(
        self,
        *,
        tenant_id: str,
        query_embedding: tuple[float, ...],
        limit: int,
        metadata_filter: Mapping[str, str] | None = None,
    ) -> tuple[SearchResult, ...]: ...

    async def delete(self, *, tenant_id: str, record_ids: Sequence[str]) -> int: ...


class InMemoryVectorStore:
    """Process-local adapter for tests and small ephemeral deployments."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], VectorRecord] = {}
        self._lock = asyncio.Lock()

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        for record in records:
            if not record.tenant_id or not record.record_id or not record.embedding:
                raise ValueError("vector records require tenant, identifier, and embedding")
        async with self._lock:
            for record in records:
                self._records[(record.tenant_id, record.record_id)] = record

    async def search(
        self,
        *,
        tenant_id: str,
        query_embedding: tuple[float, ...],
        limit: int,
        metadata_filter: Mapping[str, str] | None = None,
    ) -> tuple[SearchResult, ...]:
        if not tenant_id or not query_embedding or limit < 1:
            raise ValueError("tenant, query embedding, and a positive limit are required")
        requested_metadata = metadata_filter or {}
        async with self._lock:
            candidates = tuple(self._records.values())
        results = [
            SearchResult(record=record, score=_cosine_similarity(query_embedding, record.embedding))
            for record in candidates
            if record.tenant_id == tenant_id
            and all(record.metadata.get(key) == value for key, value in requested_metadata.items())
        ]
        results.sort(key=lambda result: (-result.score, result.record.record_id))
        return tuple(results[:limit])

    async def delete(self, *, tenant_id: str, record_ids: Sequence[str]) -> int:
        deleted = 0
        async with self._lock:
            for record_id in record_ids:
                if self._records.pop((tenant_id, record_id), None) is not None:
                    deleted += 1
        return deleted


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("query and stored embeddings must have the same dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
