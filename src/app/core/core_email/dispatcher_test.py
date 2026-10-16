from collections.abc import Callable

from app.core.core_email import (
    EmailDeliveryMode,
    EmailDispatcher,
    EmailMessage,
    register_celery_email_task,
)


class RecordingBackend:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


class RecordingQueue:
    def __init__(self, *, fails: bool = False) -> None:
        self.fails = fails
        self.messages: list[EmailMessage] = []

    async def enqueue(self, message: EmailMessage) -> None:
        if self.fails:
            raise ConnectionError("broker unavailable")
        self.messages.append(message)

    async def close(self) -> None:
        return None


def make_message() -> EmailMessage:
    return EmailMessage(subject="Welcome", recipients=("person@example.com",), text="Hello")


async def test_dispatcher_queues_when_queue_is_available() -> None:
    backend = RecordingBackend()
    queue = RecordingQueue()

    result = await EmailDispatcher(backend, queue).send(make_message())

    assert result is EmailDeliveryMode.QUEUED
    assert len(queue.messages) == 1
    assert backend.messages == []


async def test_dispatcher_falls_back_to_direct_delivery() -> None:
    backend = RecordingBackend()

    result = await EmailDispatcher(backend, RecordingQueue(fails=True)).send(make_message())

    assert result is EmailDeliveryMode.DIRECT_FALLBACK
    assert len(backend.messages) == 1


async def test_dispatcher_sends_directly_without_queue() -> None:
    backend = RecordingBackend()

    result = await EmailDispatcher(backend).send(make_message())

    assert result is EmailDeliveryMode.DIRECT
    assert len(backend.messages) == 1


class FakeCeleryApp:
    def __init__(self) -> None:
        self.task_name: str | None = None

    def task(self, *, name: str) -> Callable[[Callable[..., None]], Callable[..., None]]:
        self.task_name = name
        return lambda fn: fn


def test_celery_worker_task_delivers_serialized_message() -> None:
    backend = RecordingBackend()
    celery_app = FakeCeleryApp()
    task = register_celery_email_task(celery_app, backend=backend)

    task(message=make_message().to_payload())

    assert celery_app.task_name == "app.core.email.send"
    assert backend.messages == [make_message()]
