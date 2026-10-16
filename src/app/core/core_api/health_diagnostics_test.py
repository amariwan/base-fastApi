import asyncio

import pytest

from app.core.core_api.health_diagnostics import health_status, make_health_result, service_startup_states
from app.core.core_api.schemas import HealthCheckResult
from app.core.core_extensions.loader import RuntimeService, ServiceRegistration


def test_make_health_result_rejects_unserializable_detail() -> None:
    with pytest.raises(TypeError, match="Unsupported runtime config value"):
        make_health_result("ok", "done", details={"object": object()})


def test_health_status_fails_when_any_check_fails() -> None:
    checks = {
        "app": HealthCheckResult(status="ok", message="ready"),
        "db": HealthCheckResult(status="fail", message="down"),
    }

    assert health_status(checks) == "fail"


def test_service_startup_states_observes_finished_task_exception() -> None:
    async def fail() -> None:
        raise RuntimeError("boom")

    async def collect() -> tuple[list[str], bool]:
        task = asyncio.create_task(fail())
        await asyncio.sleep(0)
        service = RuntimeService(registration=ServiceRegistration(name="demo"), startup_results=[task])
        return service_startup_states(service)

    states, ok = asyncio.run(collect())

    assert states == ["failed: boom"]
    assert not ok
