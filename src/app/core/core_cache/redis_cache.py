"""Compatibility imports; implementation lives in base_fastapi_core."""

from base_fastapi_core.cache.redis_cache import RedisCache, RedisClient

__all__ = ["RedisCache", "RedisClient"]
