# base-fastapi-core

A versioned, installable Python library of reusable infrastructure components.
It must not depend on the application package named `app`.

The first extracted feature is cache: in-process TTL/LRU, async JSON cache,
Redis support, validated settings, and lazy backend selection.

Use the stable public API:

```python
from base_fastapi_core.cache import MemoryAsyncCache, MemoryTTLCache
```

Redis support is optional (`base-fastapi-core[redis]`).
Existing consumers of `app.core.core_cache` remain supported
through temporary compatibility modules in the source application.
