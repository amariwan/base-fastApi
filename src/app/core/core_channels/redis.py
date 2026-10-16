"""Redis Pub/Sub channel layer for multi-process WebSocket fan-out."""

from __future__ import annotations

import json
from typing import Protocol, cast

from app.shared.types import JSONValue


class RedisPubSub(Protocol):
    async def subscribe(self, *channels: str) -> None: ...

    async def unsubscribe(self, *channels: str) -> None: ...

    async def get_message(self, **options: object) -> dict[str, object] | None: ...

    async def aclose(self) -> None: ...


class RedisClient(Protocol):
    async def publish(self, channel: str, message: str) -> int: ...

    def pubsub(self) -> RedisPubSub: ...

    async def aclose(self) -> None: ...


class RedisChannelSubscription:
    def __init__(self, pubsub: RedisPubSub, channel: str) -> None:
        self._pubsub = pubsub
        self._channel = channel
        self._closed = False

    def __aiter__(self) -> RedisChannelSubscription:
        return self

    async def __anext__(self) -> JSONValue:
        while not self._closed:
            item = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if item is None:
                continue
            raw = item.get("data")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            if isinstance(raw, str):
                return cast(JSONValue, json.loads(raw))
        raise StopAsyncIteration

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._pubsub.unsubscribe(self._channel)
        await self._pubsub.aclose()


class RedisChannelLayer:
    def __init__(self, client: RedisClient, *, prefix: str = "app:channels") -> None:
        self._client = client
        self._prefix = prefix.strip(":")

    def _channel(self, channel: str) -> str:
        return f"{self._prefix}:{channel}" if self._prefix else channel

    async def publish(self, channel: str, message: JSONValue) -> int:
        return await self._client.publish(self._channel(channel), json.dumps(message, separators=(",", ":")))

    async def subscribe(self, channel: str) -> RedisChannelSubscription:
        namespaced_channel = self._channel(channel)
        pubsub = self._client.pubsub()
        await pubsub.subscribe(namespaced_channel)
        return RedisChannelSubscription(pubsub, namespaced_channel)

    async def close(self) -> None:
        await self._client.aclose()


__all__ = ["RedisChannelLayer", "RedisChannelSubscription"]
