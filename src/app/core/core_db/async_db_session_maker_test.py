import asyncio
import contextlib
from collections.abc import AsyncIterator
from typing import Protocol

from app.core.core_db.async_db_session_maker import ensure_db_schema
from pytest import MonkeyPatch


class RunSyncFn(Protocol):
    def __call__(self, conn: object) -> object: ...


class _DummyConnection:
    def __init__(self) -> None:
        self.run_sync_called = False
        self.run_sync_fn: RunSyncFn | None = None

    async def run_sync(self, fn: RunSyncFn) -> None:
        self.run_sync_called = True
        self.run_sync_fn = fn


class _DummyEngine:
    def __init__(self, connection: _DummyConnection) -> None:
        self._connection = connection

    @contextlib.asynccontextmanager
    async def begin(self) -> AsyncIterator[_DummyConnection]:
        yield self._connection


def test_ensure_db_schema_fetches_engine_from_manager(monkeypatch: MonkeyPatch) -> None:
    class DummyDbSettings:
        DB_ENABLED = True
        DB_AUTO_CREATE_TABLES = True

    # Force ensure_db_schema into the active path.
    def get_dummy_db_settings() -> DummyDbSettings:
        return DummyDbSettings()

    monkeypatch.setattr(
        "app.core.core_db.async_db_session_maker.get_db_settings",
        get_dummy_db_settings,
    )

    dummy_connection = _DummyConnection()
    dummy_engine = _DummyEngine(dummy_connection)

    class DummySessionManager:
        engine = dummy_engine

    def get_dummy_sessionmanager() -> DummySessionManager:
        return DummySessionManager()

    monkeypatch.setattr(
        "app.core.core_db.async_db_session_maker.get_sessionmanager",
        get_dummy_sessionmanager,
    )

    asyncio.run(ensure_db_schema())

    assert dummy_connection.run_sync_called
    assert getattr(dummy_connection.run_sync_fn, "__name__", "") == "create_all"
