from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from app.core.core_db.connection import build_sync_database_url

logger = logging.getLogger("app_logger")


def get_alembic_ini_path() -> str:
    # alembic.ini lives at the backend project root (one level above src/)
    # Path(__file__).parents[4] resolves to the backend folder from this file.
    return str(Path(__file__).resolve().parents[4] / "alembic.ini")


async def run_alembic_upgrade_head() -> None:
    """Run `alembic upgrade head` programmatically using alembic API.

    This runs in a thread to avoid blocking the event loop.
    The DB URL is set from application settings (sync URL) so alembic uses the correct DB.
    """
    ini = get_alembic_ini_path()
    cfg = Config(ini)
    # Ensure alembic uses the runtime DB URL (sync driver)
    cfg.set_main_option("sqlalchemy.url", build_sync_database_url())

    try:
        await asyncio.to_thread(command.upgrade, cfg, "head")
        logger.info("Alembic upgrade head completed")
    except Exception:
        logger.exception("Alembic upgrade failed")
        raise


__all__ = ["get_alembic_ini_path", "run_alembic_upgrade_head"]
