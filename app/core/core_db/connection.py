from __future__ import annotations

from app.config import DbSettings, get_db_settings
from app.core.core_messages import MessageKeys, msg


def build_async_database_url(db_settings: DbSettings | None = None) -> str:
    settings = db_settings or get_db_settings()
    if not settings.DB_ENABLED:
        raise RuntimeError(msg.get(MessageKeys.DB_DISABLED))

    return (
        f"postgresql+asyncpg://{settings.DB_USERNAME}:{settings.DB_PASSWORD}"
        f"@{settings.DB_IP}:{settings.DB_PORT}/{settings.DB_DATABASE}"
    )


def build_sync_database_url(db_settings: DbSettings | None = None) -> str:
    settings = db_settings or get_db_settings()
    if not settings.DB_ENABLED:
        raise RuntimeError(msg.get(MessageKeys.DB_DISABLED))

    return (
        f"postgresql+psycopg://{settings.DB_USERNAME}:{settings.DB_PASSWORD}"
        f"@{settings.DB_IP}:{settings.DB_PORT}/{settings.DB_DATABASE}"
    )


__all__ = ["build_async_database_url", "build_sync_database_url"]
