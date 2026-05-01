import asyncio
from contextlib import suppress
from typing import Any, cast

from app.core.core_extensions.loader import (
    RuntimeService,
    ServiceRegistration,
    _maybe_await,
    run_service_shutdown,
)
from fastapi import FastAPI


def test_maybe_await_returns_task_without_awaiting() -> None:
    async def _run() -> str:
        task: asyncio.Task[str] = asyncio.create_task(asyncio.sleep(0, result="done"))
        try:
            returned = await _maybe_await(task)
            assert returned is task
            return cast(str, await returned)
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    assert asyncio.run(_run()) == "done"


def test_run_service_shutdown_uses_lifo_hook_order() -> None:
    calls: list[tuple[str, str | None]] = []

    async def hook_one(_: FastAPI, startup_result: Any) -> None:
        calls.append(("hook_one", startup_result))

    async def hook_two(_: FastAPI, startup_result: Any) -> None:
        calls.append(("hook_two", startup_result))

    runtime = RuntimeService(
        registration=ServiceRegistration(
            name="docgen-test",
            shutdown_hooks=[hook_one, hook_two],
        ),
        startup_results=["startup_one", "startup_two"],
    )

    asyncio.run(run_service_shutdown(FastAPI(), [runtime]))
    assert calls == [
        ("hook_two", "startup_two"),
        ("hook_one", "startup_one"),
    ]
