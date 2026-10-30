"""Compatibility imports; implementation lives in base_fastapi_core."""

from base_fastapi_core.cache.settings import CacheBackend, CacheSettings, get_cache_settings

__all__ = ["CacheBackend", "CacheSettings", "get_cache_settings"]
