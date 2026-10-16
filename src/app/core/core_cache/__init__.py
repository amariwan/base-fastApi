"""Reusable caching primitives for the whole backend."""

from app.core.core_cache.async_cache import AsyncCache, MemoryAsyncCache
from app.core.core_cache.factory import close_cache, get_cache
from app.core.core_cache.memory_cache import MemoryTTLCache
from app.core.core_cache.redis_cache import RedisCache
from app.core.core_cache.settings import CacheBackend, CacheSettings, get_cache_settings

__all__ = [
    "AsyncCache",
    "CacheBackend",
    "CacheSettings",
    "MemoryAsyncCache",
    "MemoryTTLCache",
    "RedisCache",
    "close_cache",
    "get_cache",
    "get_cache_settings",
]
