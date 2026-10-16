# Core Cache

`get_cache()` returns an async, JSON-only cache. The default process-local
backend requires no external service. Set `CACHE_BACKEND=redis` and
`CACHE_REDIS_URL` for shared cache state, then install the optional client with
`uv sync --extra redis`.

Redis keys are namespaced with `CACHE_KEY_PREFIX`. `clear()` removes only that
namespace and never flushes the whole Redis database.
