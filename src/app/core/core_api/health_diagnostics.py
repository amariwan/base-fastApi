"""Pure health-diagnostic formatting and status helpers.

This module deliberately has no FastAPI route registration and performs no
external probes. It converts already collected diagnostic values into the
typed API schema used by the health endpoints.
"""

import asyncio
from collections.abc import Mapping
from typing import TypeGuard, cast

from app.core.core_extensions.loader import RuntimeService

from .schemas import HealthCheckResult, HealthCheckStatus, HealthStatus, RuntimeConfigSection, RuntimeConfigValue


def make_health_result(
    status: HealthCheckStatus,
    message: str,
    *,
    details: Mapping[str, object] | None = None,
) -> HealthCheckResult:
    """Build a schema-valid result from diagnostic values."""

    def _is_string_list(value: object) -> TypeGuard[list[str]]:
        if not isinstance(value, list):
            return False
        return all(isinstance(item, str) for item in cast(list[object], value))

    def _encode_runtime_value(value: object) -> RuntimeConfigValue:
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if _is_string_list(value):
            return list(value)
        raise TypeError(f"Unsupported runtime config value type: {type(value).__name__}")

    def _to_runtime_section(payload: Mapping[str, object]) -> RuntimeConfigSection:
        return {key: _encode_runtime_value(value) for key, value in payload.items()}

    return HealthCheckResult(status=status, message=message, details=_to_runtime_section(details or {}))


def service_startup_states(runtime_service: RuntimeService | None) -> tuple[list[str], bool]:
    """Summarize startup hook results without probing or mutating them."""
    if runtime_service is None:
        return [], True

    states: list[str] = []
    ok = True
    for result in runtime_service.startup_results:
        if result is None or isinstance(result, (bool, int, float, str)):
            states.append("completed")
            continue
        if isinstance(result, Exception):
            states.append(f"failed: {result}")
            ok = False
            continue
        if isinstance(result, asyncio.Future):
            if result.cancelled():
                states.append("cancelled")
                ok = False
                continue
            if not result.done():
                states.append("running")
                continue
            task_exception = result.exception()
            if task_exception is not None:
                states.append(f"failed: {task_exception}")
                ok = False
                continue
            states.append("completed")
            continue
        states.append(type(result).__name__)
    return states, ok


def health_status(checks: Mapping[str, HealthCheckResult]) -> HealthStatus:
    """Return failed when at least one collected check failed."""
    return "fail" if any(result.status == "fail" for result in checks.values()) else "ok"


__all__ = ["health_status", "make_health_result", "service_startup_states"]
