from app.core.core_cache import MemoryTTLCache


def test_memory_ttl_cache_returns_cached_value() -> None:
    cache = MemoryTTLCache[str, str](ttl_seconds=60, max_entries=2)

    cache.set("a", "value")

    assert cache.get("a") == "value"


def test_memory_ttl_cache_expires_entries() -> None:
    now = 100.0

    def fake_time() -> float:
        return now

    cache = MemoryTTLCache[str, str](ttl_seconds=10, max_entries=2, time_fn=fake_time)
    cache.set("a", "value")

    now = 111.0

    assert cache.get("a") is None


def test_memory_ttl_cache_evicts_oldest_entry() -> None:
    cache = MemoryTTLCache[str, str](ttl_seconds=60, max_entries=2)

    cache.set("a", "first")
    cache.set("b", "second")
    cache.set("c", "third")

    assert cache.get("a") is None
    assert cache.get("b") == "second"
    assert cache.get("c") == "third"
