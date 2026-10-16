"""Lazy cache backend selection."""

from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from typing import Protocol, cast

from app.core.core_cache.async_cache import AsyncCache, MemoryAsyncCache
from app.core.core_cache.redis_cache import RedisCache, RedisClient
from app.core.core_cache.settings import CacheBackend, get_cache_settings


class _RedisFactory(Protocol):
    def from_url(self, url: str | None, *, decode_responses: bool) -> object: ...


@lru_cache(maxsize=1)
def get_cache() -> AsyncCache:
    settings = get_cache_settings()
    if settings.CACHE_BACKEND is CacheBackend.MEMORY:
        return MemoryAsyncCache(
            ttl_seconds=settings.CACHE_DEFAULT_TTL_SECONDS,
            max_entries=settings.CACHE_MAX_ENTRIES,
        )

    try:
        redis_factory = cast(_RedisFactory, vars(import_module("redis.asyncio"))["Redis"])
    except ImportError as exc:
        raise RuntimeError("Redis cache requires the 'redis' project extra") from exc

    client = cast(RedisClient, redis_factory.from_url(settings.CACHE_REDIS_URL, decode_responses=False))
    return RedisCache(
        client,
        key_prefix=settings.CACHE_KEY_PREFIX,
        default_ttl_seconds=settings.CACHE_DEFAULT_TTL_SECONDS,
    )


async def close_cache() -> None:
    """Close the cached backend if it was initialized."""

    if get_cache.cache_info().currsize == 0:
        return
    cache = get_cache()
    get_cache.cache_clear()
    await cache.close()


__all__ = ["close_cache", "get_cache"]
