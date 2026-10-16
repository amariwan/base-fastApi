"""Lazy optional channel-layer factory."""

from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from typing import Protocol, cast

from app.core.core_channels.layer import ChannelLayer
from app.core.core_channels.memory import MemoryChannelLayer
from app.core.core_channels.redis import RedisChannelLayer, RedisClient
from app.core.core_channels.settings import ChannelBackend, get_channel_settings


class _RedisFactory(Protocol):
    def from_url(self, url: str | None, *, decode_responses: bool) -> object: ...


@lru_cache(maxsize=1)
def get_channel_layer() -> ChannelLayer | None:
    settings = get_channel_settings()
    if not settings.CHANNELS_ENABLED:
        return None
    if settings.CHANNELS_BACKEND is ChannelBackend.MEMORY:
        return MemoryChannelLayer(queue_size=settings.CHANNELS_QUEUE_SIZE)

    try:
        redis_factory = cast(_RedisFactory, vars(import_module("redis.asyncio"))["Redis"])
    except ImportError as exc:
        raise RuntimeError("Redis channels require the 'redis' project extra") from exc
    client = cast(RedisClient, redis_factory.from_url(settings.CHANNELS_REDIS_URL, decode_responses=False))
    return RedisChannelLayer(client, prefix=settings.CHANNELS_PREFIX)


async def close_channel_layer() -> None:
    """Close the cached channel layer if it was initialized."""

    if get_channel_layer.cache_info().currsize == 0:
        return
    layer = get_channel_layer()
    get_channel_layer.cache_clear()
    if layer is not None:
        await layer.close()


__all__ = ["close_channel_layer", "get_channel_layer"]
