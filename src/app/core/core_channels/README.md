# Core Channels

`core_channels` is an optional Pub/Sub layer for FastAPI WebSockets. It is
disabled by default. Enable it with `CHANNELS_ENABLED=true`; the memory backend
supports one process, while the Redis backend supports fan-out across workers.

`WebSocketChannel.stream()` is a thin outbound adapter. Business services
publish JSON-compatible events through `ChannelLayer`; API routers decide the
route, authentication, channel authorization, and disconnect policy.
The memory backend uses bounded per-subscriber queues and drops the oldest
pending event when a slow subscriber's queue is full.

The Redis backend requires `uv sync --extra redis`, `CHANNELS_BACKEND=redis`,
and `CHANNELS_REDIS_URL`.
