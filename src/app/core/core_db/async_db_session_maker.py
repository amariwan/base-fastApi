from __future__ import annotations

import contextlib
import functools
from asyncio import AbstractEventLoop, get_running_loop
from collections.abc import AsyncGenerator

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
        self._host = host
        self._engine_kwargs = dict(engine_kwargs or {})
        engine: AsyncEngine = create_async_engine(host, **self._engine_kwargs)
        sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            autocommit=False,
            bind=engine,
            expire_on_commit=False,
        )

        self._engine: AsyncEngine | None = engine
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = sessionmaker
        self._bound_loop: AbstractEventLoop | None = None

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
            self._bound_loop = None

    @property
    def engine(self) -> AsyncEngine | None:
        return self._engine

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncConnection]:
        await self._ensure_current_loop()
        if self._engine is None:
            raise RuntimeError(msg.get(MessageKeys.DB_SESSION_MANAGER_UNINITIALIZED))

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        await self._ensure_current_loop()
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

    async def _ensure_current_loop(self) -> None:
        """Rebind the cached manager when an application uses another event loop.

        SQLAlchemy's async pools retain loop-bound driver connections. This is
        common in TestClient/CLI scenarios where a cached application service
        is reused across short-lived loops. Replacing the pool with
        ``close=False`` avoids trying to close driver objects on the wrong
        loop; normal application lifecycles still use one pooled engine.
        """
        current_loop = get_running_loop()
        if self._bound_loop is current_loop:
            return
        if self._engine is None:
            raise RuntimeError(msg.get(MessageKeys.DB_SESSION_MANAGER_UNINITIALIZED))

        if self._bound_loop is not None:
            await self._engine.dispose(close=False)
            self._engine = create_async_engine(self._host, **self._engine_kwargs)
            self._sessionmaker = async_sessionmaker(
                autocommit=False,
                bind=self._engine,
                expire_on_commit=False,
            )
        self._bound_loop = current_loop


@functools.cache
def get_sessionmanager() -> DatabaseSessionManager:
    db_settings = get_db_settings()
    connection_string = build_async_database_url(db_settings)
    engine_kwargs: dict[str, object] = {
        "echo": db_settings.DB_ENGINE_ECHO,
        "pool_pre_ping": db_settings.DB_POOL_PRE_PING,
    }
    if db_settings.DB_BACKEND != "sqlite":
        engine_kwargs.update(
            pool_size=db_settings.DB_POOL_SIZE,
            max_overflow=db_settings.DB_MAX_OVERFLOW,
            pool_recycle=db_settings.DB_POOL_RECYCLE,
        )
    return DatabaseSessionManager(connection_string, engine_kwargs=engine_kwargs)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
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

    # Register built-in Core models without creating engines or connections at import time.
    from app.core.core_users.model import User  # noqa: F401

    session_manager = get_sessionmanager()
    ensure_current_loop = getattr(session_manager, "_ensure_current_loop", None)
    if ensure_current_loop is not None:
        await ensure_current_loop()
    engine = session_manager.engine
    if engine is None:
        raise RuntimeError(msg.get(MessageKeys.DB_ENGINE_UNINITIALIZED))

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
