from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.core.core_db.async_db_session_maker import get_sessionmanager
from app.core.core_db.connection import build_sync_database_url
from app.core.core_db.migrations import get_alembic_ini_path
from app.core.core_storage import get_storage_client
from sqlalchemy import create_engine, text

if TYPE_CHECKING:
    from app.config import AppSettings, DbSettings

logger = logging.getLogger("app_logger")

EnsureDbSchemaFn = Callable[[], Awaitable[None]]


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
        engine = mgr.engine
        if engine is None:
            return False, "engine not initialized"
        try:
            async with engine.connect() as conn:
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


async def get_alembic_heads_and_db_revision(timeout_seconds: int = 5) -> tuple[list[str], str | None]:
    def _sync() -> tuple[list[str], str | None]:
        ini = get_alembic_ini_path()
        cfg = Config(ini)
        sqlalchemy_url = build_sync_database_url()
        cfg.set_main_option("sqlalchemy.url", sqlalchemy_url)

        script = ScriptDirectory.from_config(cfg)
        heads = script.get_heads()

        engine = create_engine(sqlalchemy_url)
        try:
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current = context.get_current_revision()
        finally:
            try:
                engine.dispose()
            except Exception:
                pass

        return heads, current

    return await asyncio.wait_for(asyncio.to_thread(_sync), timeout=timeout_seconds)


async def migrations_needed(timeout_seconds: int = 5) -> tuple[bool, str]:
    try:
        heads, current = await get_alembic_heads_and_db_revision(timeout_seconds=timeout_seconds)
    except TimeoutError:
        return True, "alembic check timeout"
    except Exception as exc:
        return True, f"alembic check failed: {exc}"

    if not heads:
        return False, "no heads found"

    # If DB has no revision yet -> migrations needed
    if current is None:
        return True, "db has no alembic revision"

    # If current matches any head and single-head, nothing to do
    if current in heads and len(heads) == 1:
        return False, f"db at head {current}"

    # Otherwise migrations appear needed
    return True, f"db revision {current} differs from heads {heads}"


def _acquire_advisory_lock_sync(sqlalchemy_url: str, key: int, wait_seconds: int = 10) -> bool:
    """Try to acquire a Postgres advisory lock in a blocking loop (sync).

    Returns True if lock was acquired within wait_seconds, False otherwise.
    """
    engine = create_engine(sqlalchemy_url)
    try:
        import time

        deadline = time.time() + wait_seconds
        with engine.connect() as conn:
            while time.time() < deadline:
                try:
                    res = conn.execute(text(f"SELECT pg_try_advisory_lock({int(key)})"))
                    row = res.fetchone()
                    if row and row[0] is True:
                        return True
                except Exception:
                    # swallow and retry until deadline
                    pass
                time.sleep(0.5)
    finally:
        try:
            engine.dispose()
        except Exception:
            pass
    return False


def _release_advisory_lock_sync(sqlalchemy_url: str, key: int) -> bool:
    engine = create_engine(sqlalchemy_url)
    try:
        with engine.connect() as conn:
            try:
                res = conn.execute(text(f"SELECT pg_advisory_unlock({int(key)})"))
                row = res.fetchone()
                return bool(row and row[0])
            except Exception:
                return False
    finally:
        try:
            engine.dispose()
        except Exception:
            pass


async def run_migrations_with_lock(
    timeout_seconds: int = 300, lock_key: int = 123456789, lock_wait_seconds: int = 10, use_lock: bool = True
) -> tuple[bool, str]:
    """Acquire advisory lock (optionally), run alembic upgrade head, release lock.

    Returns (success, message).
    """
    # local import to avoid circular import at module import time
    from app.core.core_db.migrations import run_alembic_upgrade_head

    sqlalchemy_url = build_sync_database_url()

    acquired = True
    if use_lock:
        try:
            acquired = await asyncio.to_thread(_acquire_advisory_lock_sync, sqlalchemy_url, lock_key, lock_wait_seconds)
        except Exception as exc:
            return False, f"failed to acquire lock: {exc}"

    if not acquired:
        return False, "could not acquire migration lock"

    try:
        await asyncio.wait_for(run_alembic_upgrade_head(), timeout=timeout_seconds)
        return True, "migrations applied"
    except TimeoutError:
        return False, "migration timeout"
    except Exception as exc:
        return False, f"migration failed: {exc}"
    finally:
        if use_lock:
            try:
                await asyncio.to_thread(_release_advisory_lock_sync, sqlalchemy_url, lock_key)
            except Exception:
                pass


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

    logger.exception("DB migration failed: %s", message)
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
