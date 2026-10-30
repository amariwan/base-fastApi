"""Compatibility imports; implementation lives in base_fastapi_core."""

from base_fastapi_core.cache.async_cache import AsyncCache, MemoryAsyncCache

__all__ = ["AsyncCache", "MemoryAsyncCache"]
