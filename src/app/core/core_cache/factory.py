"""Compatibility imports; implementation lives in base_fastapi_core."""

from base_fastapi_core.cache.factory import close_cache, get_cache

__all__ = ["close_cache", "get_cache"]
