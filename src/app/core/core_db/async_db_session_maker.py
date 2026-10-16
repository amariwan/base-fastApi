from __future__ import annotations

import contextlib
import functools
from collections.abc import AsyncIterator

from app.config import get_db_settings
from app.core.core_db.base import Base
from app.core.core_db.connection import build_async_database_url
from app.core.core_messages import MessageKeys, msg
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class DatabaseSessionManager:
    """
    Manages a single async SQLAlchemy Engine and provides async session and connection context managers.

    Responsibilities:
    - Creates and maintains a single, heavy-weight AsyncEngine instance.
    - Provides `session()` context manager for safe AsyncSession usage (auto rollback/close).
    - Provides `connect()` context manager for raw AsyncConnection usage.
    - Supports async cleanup of engine resources via `close()`.

    Usage:
        session_manager = DatabaseSessionManager(connection_string)
        async with session_manager.session() as session:
            result = await session.execute(some_query)
    """

    def __init__(self, host: str, engine_kwargs: dict[str, object] | None = None):
        engine: AsyncEngine = create_async_engine(host, **(engine_kwargs or {}))
        sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            autocommit=False,
            bind=engine,
            expire_on_commit=False,
        )

        self._engine: AsyncEngine | None = engine
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = sessionmaker

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None

    @property
    def engine(self) -> AsyncEngine | None:
        return self._engine

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise RuntimeError(msg.get(MessageKeys.DB_SESSION_MANAGER_UNINITIALIZED))

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise RuntimeError(msg.get(MessageKeys.DB_SESSION_MANAGER_UNINITIALIZED))

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@functools.cache
def get_sessionmanager() -> DatabaseSessionManager:
    db_settings = get_db_settings()
    connection_string = build_async_database_url(db_settings)
    return DatabaseSessionManager(
        connection_string,
        engine_kwargs={
            "echo": db_settings.DB_ENGINE_ECHO,
            "pool_size": db_settings.DB_POOL_SIZE,
            "max_overflow": db_settings.DB_MAX_OVERFLOW,
            "pool_recycle": db_settings.DB_POOL_RECYCLE,
            "pool_pre_ping": db_settings.DB_POOL_PRE_PING,
        },
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an async DB session.

    Handles rollback on exceptions and session closure automatically.
    Commits must be performed explicitly by the caller or service layer.
    """
    async with get_sessionmanager().session() as session:
        yield session


async def ensure_db_schema() -> None:
    """Create missing tables from SQLAlchemy metadata if DB auto create is enabled."""
    db_settings = get_db_settings()
    if not db_settings.DB_ENABLED or not db_settings.DB_AUTO_CREATE_TABLES:
        return

    engine = get_sessionmanager().engine
    if engine is None:
        raise RuntimeError(msg.get(MessageKeys.DB_ENGINE_UNINITIALIZED))

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
