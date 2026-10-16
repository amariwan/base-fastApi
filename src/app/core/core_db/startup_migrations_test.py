import asyncio
from unittest.mock import AsyncMock, patch

from app.core.core_db import startup_migrations


def test_run_migrations_without_lock_reports_success() -> None:
    with (
        patch("app.core.core_db.startup_migrations.build_sync_database_url", return_value="postgresql://db"),
        patch("app.core.core_db.migrations.run_alembic_upgrade_head", new=AsyncMock()),
    ):
        result = asyncio.run(startup_migrations.run_migrations_with_lock(use_lock=False))

    assert result == (True, "migrations applied")
