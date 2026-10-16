"""Alembic revision checks and serialized startup migration execution."""

from __future__ import annotations

import asyncio
import time

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.core.core_db.connection import build_sync_database_url
from app.core.core_db.migrations import get_alembic_ini_path
from sqlalchemy import create_engine, make_url, text


async def get_alembic_heads_and_db_revision(timeout_seconds: int = 5) -> tuple[list[str], str | None]:
    """Read migration heads and the current database revision off the event loop."""

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
            engine.dispose()

        return heads, current

    return await asyncio.wait_for(asyncio.to_thread(_sync), timeout=timeout_seconds)


async def migrations_needed(timeout_seconds: int = 5) -> tuple[bool, str]:
    """Return whether the database revision differs from the single head."""
    try:
        heads, current = await get_alembic_heads_and_db_revision(timeout_seconds=timeout_seconds)
    except TimeoutError:
        return True, "alembic check timeout"
    except Exception as exc:
        return True, f"alembic check failed: {exc}"

    if not heads:
        return False, "no heads found"
    if current is None:
        return True, "db has no alembic revision"
    if current in heads and len(heads) == 1:
        return False, f"db at head {current}"
    return True, f"db revision {current} differs from heads {heads}"


def _acquire_advisory_lock_sync(sqlalchemy_url: str, key: int, wait_seconds: int = 10) -> bool:
    """Try to acquire a PostgreSQL advisory lock within the configured wait time."""
    engine = create_engine(sqlalchemy_url)
    try:
        deadline = time.time() + wait_seconds
        with engine.connect() as conn:
            while time.time() < deadline:
                try:
                    result = conn.execute(text(f"SELECT pg_try_advisory_lock({int(key)})"))
                    row = result.fetchone()
                    if row and row[0] is True:
                        return True
                except Exception:
                    pass
                time.sleep(0.5)
    finally:
        engine.dispose()
    return False


def _release_advisory_lock_sync(sqlalchemy_url: str, key: int) -> bool:
    """Release a PostgreSQL advisory lock and report whether it was held."""
    engine = create_engine(sqlalchemy_url)
    try:
        with engine.connect() as conn:
            try:
                result = conn.execute(text(f"SELECT pg_advisory_unlock({int(key)})"))
                row = result.fetchone()
                return bool(row and row[0])
            except Exception:
                return False
    finally:
        engine.dispose()


async def run_migrations_with_lock(
    timeout_seconds: int = 300,
    lock_key: int = 123456789,
    lock_wait_seconds: int = 10,
    use_lock: bool = True,
) -> tuple[bool, str]:
    """Run Alembic upgrade head, serializing concurrent application starts."""
    from app.core.core_db.migrations import run_alembic_upgrade_head

    sqlalchemy_url = build_sync_database_url()
    acquired = True
    supports_advisory_lock = make_url(sqlalchemy_url).get_backend_name() == "postgresql"
    if use_lock and supports_advisory_lock:
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
        if use_lock and supports_advisory_lock:
            try:
                await asyncio.to_thread(_release_advisory_lock_sync, sqlalchemy_url, lock_key)
            except Exception:
                pass


__all__ = ["get_alembic_heads_and_db_revision", "migrations_needed", "run_migrations_with_lock"]
