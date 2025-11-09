from __future__ import annotations

import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import DbSettings, get_app_settings, get_db_settings
from db import db
from shared.logging.AppLogger import setup_logging, system_logger


def _is_pytest() -> bool:
    """Check if running under pytest."""
    return "pytest" in sys.modules or bool(os.getenv("PYTEST_CURRENT_TEST"))


def _should_skip_db_init(app_settings) -> bool:
    """Determine if DB initialization should be skipped."""
    is_test = getattr(app_settings, "TEST_MODE", False) or _is_pytest()
    env_value = getattr(app_settings, "APP_ENV", getattr(app_settings, "ENV", "dev"))
    is_local = (env_value or "dev").lower() in {
        "dev",
        "local",
    }
    return is_test or is_local


async def _setup_application(app: FastAPI) -> tuple:
    """Setup application settings and logging."""
    setup_logging()
    app_settings = get_app_settings()
    try:
        db_settings = get_db_settings()
    except SystemExit as e:
        system_logger.error("Failed to load DB settings", exc_info=True)
        raise RuntimeError("Database configuration error") from e

    system_logger.info(
        "Starting app",
        extra={
            "LOG_LEVEL": getattr(app_settings, "LOG_LEVEL", None),
            "DB": getattr(db_settings, "DB_DATABASE", None),
            "PORT": getattr(db_settings, "DB_PORT", None),
        },
    )
    return app_settings, db_settings


async def _initialize_database(db_settings: DbSettings, skip_db_init: bool) -> None:
    """Initialize database models if not skipping."""
    if skip_db_init:
        system_logger.info("Skipping DB init & migrations")
        return

    try:
        await db.init_models()
        system_logger.info("Database initialized successfully")
    except Exception as exc:
        system_logger.error("DB init failed", extra={"error": str(exc)}, exc_info=True)
        raise


async def _start_scheduler_if_enabled() -> None:
    """Start auto-publish scheduler if enabled."""
    if os.getenv("SCHEDULER_ENABLED", "true").lower() == "true":
        interval = int(os.getenv("AUTO_PUBLISH_INTERVAL_SECONDS", "60"))
        system_logger.info(
            "Auto-publish scheduler started", extra={"interval": interval}
        )


async def _cleanup_database(skip_db_init: bool) -> None:
    """Dispose database connection if initialized."""
    if skip_db_init:
        return

    try:
        await db.dispose()
        system_logger.info("Database disposed successfully")
    except Exception as exc:
        system_logger.error(
            "DB dispose failed", extra={"error": str(exc)}, exc_info=True
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager."""
    app_settings, db_settings = await _setup_application(app)
    skip_db_init = _should_skip_db_init(app_settings)

    await _initialize_database(db_settings, skip_db_init)
    await _start_scheduler_if_enabled()

    try:
        yield
    finally:
        await _cleanup_database(skip_db_init)
        system_logger.info("Shutdown complete", extra={"skip_db_dispose": skip_db_init})
