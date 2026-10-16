from collections.abc import AsyncIterator

from app.core.core_cache.redis_cache import RedisCache


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.closed = False

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
        self.closed = True


async def test_redis_cache_namespaces_json_values_and_clears_only_its_prefix() -> None:
    client = FakeRedis()
    client.values["other:key"] = '"preserved"'
    cache = RedisCache(client, key_prefix="service", default_ttl_seconds=60)

    await cache.set("user", {"id": "123"})

    assert await cache.get("user") == {"id": "123"}
    assert "service:user" in client.values
    await cache.clear()
    assert client.values == {"other:key": '"preserved"'}


async def test_redis_cache_zero_ttl_removes_existing_value() -> None:
    client = FakeRedis()
    cache = RedisCache(client)
    await cache.set("temporary", "old")

    await cache.set("temporary", "new", ttl_seconds=0)

    assert await cache.get("temporary") is None
