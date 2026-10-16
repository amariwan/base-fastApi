from __future__ import annotations

from app.config import DbSettings, get_db_settings
from app.core.core_messages import MessageKeys, msg
from sqlalchemy import URL

_DEFAULT_PORTS = {"postgresql": 5432, "mysql": 3306}


def _build_database_url(*, asynchronous: bool, db_settings: DbSettings | None = None) -> str:
    settings = db_settings or get_db_settings()
    if not settings.DB_ENABLED:
        raise RuntimeError(msg.get(MessageKeys.DB_DISABLED))

    if settings.DB_BACKEND == "sqlite":
        driver = "sqlite+aiosqlite" if asynchronous else "sqlite+pysqlite"
        return URL.create(driver, database=settings.DB_DATABASE).render_as_string(hide_password=False)

    driver = {
        ("postgresql", True): "postgresql+asyncpg",
        ("postgresql", False): "postgresql+psycopg",
        ("mysql", True): "mysql+asyncmy",
        ("mysql", False): "mysql+pymysql",
    }[(settings.DB_BACKEND, asynchronous)]
    return URL.create(
        driver,
        username=settings.DB_USERNAME,
        password=settings.DB_PASSWORD,
        host=settings.DB_IP,
        port=settings.DB_PORT or _DEFAULT_PORTS[settings.DB_BACKEND],
        database=settings.DB_DATABASE,
    ).render_as_string(hide_password=False)


def build_async_database_url(db_settings: DbSettings | None = None) -> str:
    return _build_database_url(asynchronous=True, db_settings=db_settings)


def build_sync_database_url(db_settings: DbSettings | None = None) -> str:
    return _build_database_url(asynchronous=False, db_settings=db_settings)


__all__ = ["build_async_database_url", "build_sync_database_url"]
