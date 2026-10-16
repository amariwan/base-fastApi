from app.core.core_cache import MemoryAsyncCache
from app.shared.types import JSONValue


async def test_memory_async_cache_supports_json_values_and_delete() -> None:
    cache = MemoryAsyncCache(ttl_seconds=60)
    value: JSONValue = {"user_id": "abc", "roles": ["reader"]}

    await cache.set("session", value)

    assert await cache.get("session") == value
    await cache.delete("session")
    assert await cache.get("session") is None


async def test_memory_async_cache_supports_per_item_ttl() -> None:
    cache = MemoryAsyncCache(ttl_seconds=60)

    await cache.set("short", "old")
    await cache.set("short", "value", ttl_seconds=0)

    assert await cache.get("short") is None
