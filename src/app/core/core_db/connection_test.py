"""Database URL coverage for every supported backend."""

import pytest
from app.config import DbSettings
from app.core.core_db.connection import build_async_database_url, build_sync_database_url


@pytest.mark.parametrize(
    ("backend", "port", "async_prefix", "sync_prefix"),
    [
        ("postgresql", 5432, "postgresql+asyncpg", "postgresql+psycopg"),
        ("mysql", 3306, "mysql+asyncmy", "mysql+pymysql"),
    ],
)
def test_build_database_urls_for_server_backends(
    backend: str,
    port: int,
    async_prefix: str,
    sync_prefix: str,
) -> None:
    settings = DbSettings(
        DB_ENABLED=True,
        DB_BACKEND=backend,
        DB_PORT=port,
        DB_USERNAME="user",
        DB_PASSWORD="p@ss",
        DB_DATABASE="example",
        DB_IP="db.local",
    )

    assert build_async_database_url(settings) == f"{async_prefix}://user:p%40ss@db.local:{port}/example"
    assert build_sync_database_url(settings) == f"{sync_prefix}://user:p%40ss@db.local:{port}/example"


def test_build_database_urls_for_sqlite() -> None:
    settings = DbSettings(DB_ENABLED=True, DB_BACKEND="sqlite", DB_DATABASE="./test.db")

    assert build_async_database_url(settings) == "sqlite+aiosqlite:///./test.db"
    assert build_sync_database_url(settings) == "sqlite+pysqlite:///./test.db"
