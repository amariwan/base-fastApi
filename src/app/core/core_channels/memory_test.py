import asyncio

from app.core.core_channels import MemoryChannelLayer


async def test_memory_channel_layer_fans_out_to_subscribers() -> None:
    layer = MemoryChannelLayer()
    first = await layer.subscribe("notifications")
    second = await layer.subscribe("notifications")

    delivered = await layer.publish("notifications", {"event": "updated"})

    assert delivered == 2
    assert await asyncio.wait_for(anext(first), timeout=0.1) == {"event": "updated"}
    assert await asyncio.wait_for(anext(second), timeout=0.1) == {"event": "updated"}
    await first.close()
    await second.close()


async def test_memory_channel_layer_unsubscribes_closed_subscription() -> None:
    layer = MemoryChannelLayer()
    subscription = await layer.subscribe("notifications")
    await subscription.close()

    assert await layer.publish("notifications", "event") == 0


async def test_memory_channel_layer_drops_oldest_message_for_slow_subscriber() -> None:
    layer = MemoryChannelLayer(queue_size=1)
    subscription = await layer.subscribe("notifications")

    await layer.publish("notifications", "old")
    await layer.publish("notifications", "latest")

    assert await anext(subscription) == "latest"
    await subscription.close()
