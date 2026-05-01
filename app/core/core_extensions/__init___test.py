import asyncio
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest
from app.core.core_extensions import loader
from app.core.core_extensions.loader import (
    RuntimeService,
    ServiceRegistration,
    discover_service_module_names,
    get_service_registrations,
    run_service_shutdown,
)
from app.core.core_messages import MessageKeys, msg
from fastapi import APIRouter, FastAPI


def test_discover_service_module_names_returns_sorted_service_integrations(tmp_path: Path) -> None:
    services_dir = tmp_path / "services"
    (services_dir / "docgen").mkdir(parents=True)
    (services_dir / "docgen" / "integration.py").write_text("", encoding="utf-8")
    (services_dir / "docmanager").mkdir(parents=True)
    (services_dir / "docmanager" / "integration.py").write_text("", encoding="utf-8")
    (services_dir / "__pycache__").mkdir(parents=True)

    modules = discover_service_module_names(services_dir)
    assert modules == [
        "app.services.docgen.integration",
        "app.services.docmanager.integration",
    ]


def test_get_service_registrations_returns_loaded_services(monkeypatch: pytest.MonkeyPatch) -> None:
    router = APIRouter()
    monkeypatch.setattr(loader, "discover_service_module_names", lambda: ["app.services.docmanager.integration"])
    monkeypatch.setattr(
        loader,
        "load_service_registrations",
        lambda _: [ServiceRegistration(name="docmanager", routers=[router])],
    )

    registrations = get_service_registrations()
    assert len(registrations) == 1
    assert registrations[0].name == "docmanager"
    assert registrations[0].routers == [router]


def test_get_service_registrations_raises_when_no_modules_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loader, "discover_service_module_names", lambda: [])
    with pytest.raises(RuntimeError) as exc_info:
        get_service_registrations()
    assert str(exc_info.value) == msg.get(MessageKeys.EXTENSIONS_NO_INTEGRATION_MODULES)


def test_get_service_registrations_raises_when_router_list_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(loader, "discover_service_module_names", lambda: ["app.services.docmanager.integration"])
    monkeypatch.setattr(
        loader,
        "load_service_registrations",
        lambda _: [ServiceRegistration(name="docmanager", routers=[])],
    )
    with pytest.raises(RuntimeError) as exc_info:
        get_service_registrations()
    assert str(exc_info.value) == msg.get(
        MessageKeys.EXTENSIONS_NO_ROUTERS_CONFIGURED,
        service="docmanager",
    )


def test_get_service_registrations_raises_when_no_service_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(loader, "discover_service_module_names", lambda: ["app.services.docmanager.integration"])
    monkeypatch.setattr(loader, "load_service_registrations", lambda _: [])
    with pytest.raises(RuntimeError) as exc_info:
        get_service_registrations()
    assert str(exc_info.value) == msg.get(
        MessageKeys.EXTENSIONS_NO_VALID_REGISTRATIONS,
        modules="app.services.docmanager.integration",
    )


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


def test_run_service_shutdown_cancels_tasks_via_hooks() -> None:
    async def _run() -> str:
        task: asyncio.Task[str] = asyncio.create_task(asyncio.sleep(0, result="done"))

        async def hook(_: FastAPI, startup_result: Any) -> None:
            assert startup_result is task
            startup_result.cancel()
            with suppress(asyncio.CancelledError):
                await startup_result

        runtime = RuntimeService(
            registration=ServiceRegistration(name="svc", shutdown_hooks=[hook]),
            startup_results=[task],
        )

        await run_service_shutdown(FastAPI(), [runtime])
        return "ok"

    assert asyncio.run(_run()) == "ok"
