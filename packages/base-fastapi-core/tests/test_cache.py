"""Independent library tests that never import the host application."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from base_fastapi_core.cache import MemoryAsyncCache, MemoryTTLCache, RedisCache


def test_memory_cache_expires_and_evicts() -> None:
    now = 100.0

    def clock() -> float:
        return now

    cache = MemoryTTLCache[str, str](ttl_seconds=10, max_entries=2, time_fn=clock)
    cache.set("old", "first")
    cache.set("new", "second")
    cache.set("latest", "third")
    assert cache.get("old") is None
    assert cache.get("new") == "second"
    now = 111.0
    assert cache.get("new") is None


@pytest.mark.asyncio
async def test_async_memory_cache_supports_ttl_and_delete() -> None:
    cache = MemoryAsyncCache(ttl_seconds=60)
    value = {"roles": ["reader"]}
    await cache.set("session", value)
    assert await cache.get("session") == value
    await cache.set("session", value, ttl_seconds=0)
    assert await cache.get("session") is None
    await cache.set("session", value)
    await cache.delete("session")
    assert await cache.get("session") is None


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int | None = None) -> None:
        self.values[key] = value

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self.values.pop(key, None)

    async def scan_iter(self, *, match: str) -> AsyncIterator[str]:
        prefix = match.removesuffix("*")
        for key in tuple(self.values):
            if key.startswith(prefix):
                yield key

    async def aclose(self) -> None:
        pass


@pytest.mark.asyncio
async def test_redis_cache_preserves_other_namespaces() -> None:
    client = FakeRedis()
    client.values["other:key"] = '"preserved"'
    cache = RedisCache(client, key_prefix="service")
    await cache.set("user", {"id": "123"})
    assert await cache.get("user") == {"id": "123"}
    await cache.clear()
    assert client.values == {"other:key": '"preserved"'}
