"""Startup-check tests for migration failure policy."""

# This test patches the private migration runner to isolate policy behaviour.
# pyright: reportPrivateUsage=false

import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest

from app.config import AppSettings
from app.core.startup_checks import _run_startup_migrations


def test_failed_startup_migration_raises_when_fail_on_error_enabled() -> None:
    settings = SimpleNamespace(
        MIGRATION_TIMEOUT_SECONDS=1,
        MIGRATIONS_ADVISORY_LOCK_KEY=123,
        MIGRATIONS_ADVISORY_LOCK_USE=True,
        STARTUP_FAIL_ON_ERROR=True,
    )

    with patch(
        "app.core.startup_checks.run_migrations_with_lock",
        new=AsyncMock(return_value=(False, "database unavailable")),
    ):
        with pytest.raises(RuntimeError, match="database unavailable"):
            asyncio.run(_run_startup_migrations(cast(AppSettings, settings)))


def test_failed_startup_migration_logs_and_continues_when_fail_on_error_disabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = SimpleNamespace(
        MIGRATION_TIMEOUT_SECONDS=1,
        MIGRATIONS_ADVISORY_LOCK_KEY=123,
        MIGRATIONS_ADVISORY_LOCK_USE=True,
        STARTUP_FAIL_ON_ERROR=False,
    )

    with patch(
        "app.core.startup_checks.run_migrations_with_lock",
        new=AsyncMock(return_value=(False, "database unavailable")),
    ):
        asyncio.run(_run_startup_migrations(cast(AppSettings, settings)))

    assert "DB migration failed: database unavailable" in caplog.text
