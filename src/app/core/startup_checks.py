from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from app.core.core_db.async_db_session_maker import get_sessionmanager
from app.core.core_db.startup_migrations import (
    get_alembic_heads_and_db_revision,
    migrations_needed,
    run_migrations_with_lock,
)
from app.core.core_storage import get_storage_client
from sqlalchemy import text

if TYPE_CHECKING:
    from app.config import AppSettings, DbSettings

logger = logging.getLogger("app_logger")

EnsureDbSchemaFn = Callable[[], Awaitable[None]]

__all__ = [
    "check_db",
    "check_s3",
    "get_alembic_heads_and_db_revision",
    "migrations_needed",
    "perform_startup_checks",
    "run_migrations_with_lock",
]


async def check_s3(timeout_seconds: int = 5) -> tuple[bool, str]:
    try:
        client = get_storage_client()
    except Exception as exc:
        return False, f"storage init failed: {exc}"

    try:
        files = await asyncio.wait_for(asyncio.to_thread(client.list_files, ""), timeout=timeout_seconds)
        return True, f"ok ({len(files)} objects)"
    except TimeoutError:
        return False, "timeout"
    except Exception as exc:
        return False, str(exc)


async def check_db(timeout_seconds: int = 5) -> tuple[bool, str]:
    async def _probe() -> tuple[bool, str]:
        mgr = get_sessionmanager()
        try:
            async with mgr.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True, "ok"
        except Exception as exc:  # pragma: no cover - runtime DB errors
            return False, str(exc)

    try:
        return await asyncio.wait_for(_probe(), timeout=timeout_seconds)
    except TimeoutError:
        return False, "timeout"
    except Exception as exc:
        return False, str(exc)


def _log_probe_result(name: str, ok: bool, message: str, *, failure_level: int = logging.WARNING) -> None:
    if ok:
        logger.info("%s probe OK: %s", name, message)
        return

    logger.log(failure_level, "%s probe failed: %s", name, message)


async def _run_startup_probes(app_settings: AppSettings) -> None:
    s3_ok, s3_msg = await check_s3(timeout_seconds=app_settings.S3_PROBE_TIMEOUT_SECONDS)
    _log_probe_result("S3", s3_ok, s3_msg)

    db_ok, db_msg = await check_db(timeout_seconds=app_settings.DB_PROBE_TIMEOUT_SECONDS)
    _log_probe_result("DB", db_ok, db_msg, failure_level=logging.ERROR)
    if not db_ok and app_settings.STARTUP_FAIL_ON_ERROR:
        raise RuntimeError("DB probe failed: " + db_msg)


def _startup_migration_mode(app_settings: AppSettings) -> str:
    if app_settings.RUN_MIGRATIONS_ON_STARTUP:
        return "always"
    return app_settings.MIGRATIONS_ON_STARTUP_MODE


async def _maybe_ensure_db_schema(
    db_settings: DbSettings, ensure_db_schema: EnsureDbSchemaFn, *, log_skip: bool = False
) -> None:
    if db_settings.DB_AUTO_CREATE_TABLES:
        await ensure_db_schema()
        return

    if log_skip:
        logger.info("DB initialization skipped (no migrations and auto-create disabled)")


async def _run_startup_migrations(app_settings: AppSettings) -> None:
    ok, message = await run_migrations_with_lock(
        timeout_seconds=app_settings.MIGRATION_TIMEOUT_SECONDS,
        lock_key=app_settings.MIGRATIONS_ADVISORY_LOCK_KEY,
        use_lock=app_settings.MIGRATIONS_ADVISORY_LOCK_USE,
    )
    if ok:
        logger.info("DB migrations applied: %s", message)
        return

    logger.error("DB migration failed: %s", message)
    if app_settings.STARTUP_FAIL_ON_ERROR:
        raise RuntimeError("DB migration failed: " + message)


async def _handle_auto_migrations(
    app_settings: AppSettings, db_settings: DbSettings, ensure_db_schema: EnsureDbSchemaFn
) -> None:
    needed, reason = await migrations_needed(timeout_seconds=app_settings.MIGRATION_TIMEOUT_SECONDS)
    if needed:
        logger.info("Migrations needed: %s — running upgrade", reason)
        await _run_startup_migrations(app_settings)
        return

    logger.info("No migrations required: %s", reason)
    await _maybe_ensure_db_schema(db_settings, ensure_db_schema)


async def _initialize_database_startup(
    app_settings: AppSettings, db_settings: DbSettings, ensure_db_schema: EnsureDbSchemaFn
) -> None:
    mode = _startup_migration_mode(app_settings)
    if mode == "never":
        logger.info("Migrations on startup disabled (mode=never)")
        await _maybe_ensure_db_schema(db_settings, ensure_db_schema, log_skip=True)
        return

    if mode == "always":
        logger.info("Migrations on startup: executing (mode=always)")
        await _run_startup_migrations(app_settings)
        return

    await _handle_auto_migrations(app_settings, db_settings, ensure_db_schema)


async def perform_startup_checks() -> None:
    """High-level orchestrator used by the application lifespan.

    This wraps S3/DB probes, migration decisions and execution and the
    optional `ensure_db_schema()` fallback. It raises on fatal errors when
    `STARTUP_FAIL_ON_ERROR` is enabled; otherwise it logs problems and
    returns normally to allow the app to start in degraded mode.
    """
    # Local imports to avoid potential import cycles at module import time
    from app.config import get_app_settings, get_db_settings
    from app.core.core_db.async_db_session_maker import ensure_db_schema

    app_settings = get_app_settings()
    db_settings = get_db_settings()

    logger.info("Starting DB/S3 startup checks")

    if not db_settings.DB_ENABLED:
        logger.info("Database disabled - skipping DB init")
        return

    logger.info(
        "Database enabled: DB=%s Port=%s",
        db_settings.DB_DATABASE,
        db_settings.DB_PORT,
    )

    await _run_startup_probes(app_settings)
    await _initialize_database_startup(app_settings, db_settings, ensure_db_schema)
