from app.core.core_channels.redis import RedisChannelLayer


class FakePubSub:
    def __init__(self) -> None:
        self.channel: str | None = None
        self.messages: list[dict[str, object]] = []

    async def subscribe(self, *channels: str) -> None:
        self.channel = channels[0]

    async def unsubscribe(self, *channels: str) -> None:
        self.channel = None

    async def get_message(self, **options: object) -> dict[str, object] | None:
        return self.messages.pop(0) if self.messages else None

    async def aclose(self) -> None:
        return None


class FakeRedis:
    def __init__(self) -> None:
        self.subscription = FakePubSub()
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1

    def pubsub(self) -> FakePubSub:
        return self.subscription

    async def aclose(self) -> None:
        return None


async def test_redis_channel_layer_namespaces_and_decodes_messages() -> None:
    client = FakeRedis()
    layer = RedisChannelLayer(client, prefix="service:channels")

    assert await layer.publish("updates", {"id": 1}) == 1
    assert client.published == [("service:channels:updates", '{"id":1}')]

    subscription = await layer.subscribe("updates")
    client.subscription.messages.append({"data": b'{"event":"ready"}'})
    assert await anext(subscription) == {"event": "ready"}
    await subscription.close()
