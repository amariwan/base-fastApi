"""Preserve class and factory identities across the extraction boundary."""

from app.core.core_cache import (
    AsyncCache,
    CacheSettings,
    MemoryAsyncCache,
    MemoryTTLCache,
    RedisCache,
    close_cache,
    get_cache,
)
from base_fastapi_core.cache import (
    AsyncCache as LibraryAsyncCache,
)
from base_fastapi_core.cache import (
    CacheSettings as LibraryCacheSettings,
)
from base_fastapi_core.cache import (
    MemoryAsyncCache as LibraryMemoryAsyncCache,
)
from base_fastapi_core.cache import (
    MemoryTTLCache as LibraryMemoryTTLCache,
)
from base_fastapi_core.cache import (
    RedisCache as LibraryRedisCache,
)
from base_fastapi_core.cache import (
    close_cache as library_close_cache,
)
from base_fastapi_core.cache import (
    get_cache as library_get_cache,
)


def test_compatibility_exports_reference_same_implementations() -> None:
    assert AsyncCache is LibraryAsyncCache
    assert CacheSettings is LibraryCacheSettings
    assert MemoryAsyncCache is LibraryMemoryAsyncCache
    assert MemoryTTLCache is LibraryMemoryTTLCache
    assert RedisCache is LibraryRedisCache
    assert close_cache is library_close_cache
    assert get_cache is library_get_cache
