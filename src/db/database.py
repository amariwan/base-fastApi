from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.logging.AppLogger import system_logger

from .dsn import build_url, masked, ssl_context
from .options import (
    APP_ENV,
    APP_NAME,
    COMMAND_TIMEOUT,
    CONNECT_TIMEOUT,
    DB_REQUIRE_SSL,
    DB_SSL_NO_VERIFY,
    MAX_OVERFLOW,
    PG_IDLE_IN_XACT_TIMEOUT_MS,
    PG_STATEMENT_TIMEOUT_MS,
    POOL_RECYCLE_SECS,
    POOL_SIZE,
    POOL_TIMEOUT,
    SKIP_STARTUP_WAIT,
    STARTUP_BASE_DELAY,
    STARTUP_MAX_DELAY,
    STARTUP_MAX_RETRIES,
    STARTUP_OVERALL_TIMEOUT,
)


class Database:
    """Async DB helper with async engine/pooling controls."""

    def __init__(self, url: URL | str | None = None, *, echo: bool = False) -> None:
        self._url: URL = (
            build_url()
            if url is None
            else (make_url(url) if isinstance(url, str) else url)
        )
        self._echo = echo
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._models_initialized = False
        self._db_ready = False
        self._db_ready_lock = asyncio.Lock()
        self._skip_startup_wait = SKIP_STARTUP_WAIT
        self._skip_wait_logged = False

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            connect_args: dict[str, object] = {
                "timeout": CONNECT_TIMEOUT,
                "command_timeout": COMMAND_TIMEOUT,
                "server_settings": {
                    "application_name": f"{APP_NAME}:{APP_ENV}",
                    "timezone": "UTC",
                    "statement_timeout": str(PG_STATEMENT_TIMEOUT_MS),
                    "idle_in_transaction_session_timeout": str(
                        PG_IDLE_IN_XACT_TIMEOUT_MS
                    ),
                },
            }

            ctx = ssl_context()
            if ctx:
                connect_args["ssl"] = ctx

            kwargs: dict[str, object] = {
                "echo": self._echo,
                "future": True,
                "pool_pre_ping": True,
                "pool_recycle": POOL_RECYCLE_SECS,
                "pool_size": POOL_SIZE,
                "max_overflow": MAX_OVERFLOW,
                "pool_timeout": POOL_TIMEOUT,
                "connect_args": connect_args,
            }

            # sqlite: inkompatible Optionen entfernen
            if "sqlite" in str(self._url).lower():
                kwargs["connect_args"] = {"timeout": CONNECT_TIMEOUT}
                for k in (
                    "pool_size",
                    "max_overflow",
                    "pool_recycle",
                    "pool_pre_ping",
                    "pool_timeout",
                ):
                    kwargs.pop(k, None)

            # Sicherheitsgurt: PROD muss SSL erzwingen
            if APP_ENV == "prod" and not DB_REQUIRE_SSL:
                system_logger.warning(
                    "PROD without DB SSL is forbidden - refusing to start"
                )
                raise RuntimeError("DB SSL required in production")
            if APP_ENV == "prod" and DB_SSL_NO_VERIFY:
                system_logger.warning(
                    "PROD with SSL_NO_VERIFY is forbidden - refusing to start"
                )
                raise RuntimeError("DB SSL verification required in production")

            self._engine = create_async_engine(self._url, **kwargs)
            system_logger.info("DB engine created", extra={"url": masked(self._url)})
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine, expire_on_commit=False, autoflush=False
            )
        return self._session_factory

    async def ping(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.exec_driver_sql("SELECT 1")
            return True
        except Exception as exc:
            system_logger.debug("DB ping failed", extra={"error": str(exc)})
            return False

    async def _wait_for_db(self) -> None:
        start = time.monotonic()
        attempt, delay = 0, STARTUP_BASE_DELAY
        while True:
            try:
                async with self.engine.connect() as conn:
                    await conn.exec_driver_sql("SELECT 1")
                if attempt:
                    system_logger.info("DB became available")
                self._db_ready = True
                return
            except Exception:
                attempt += 1
                elapsed = time.monotonic() - start
                if elapsed > STARTUP_OVERALL_TIMEOUT or attempt > STARTUP_MAX_RETRIES:
                    system_logger.error(
                        "DB connection failed",
                        extra={"attempts": attempt, "elapsed": elapsed},
                        exc_info=True,
                    )
                    raise
                # jitter
                wait = min(
                    delay * (0.9 + int.from_bytes(os.urandom(1), "little") / 1275.0),
                    STARTUP_MAX_DELAY,
                )
                system_logger.warning(
                    "DB not ready - retrying",
                    extra={"attempt": attempt, "wait": round(wait, 2)},
                )
                await asyncio.sleep(max(0.1, wait))
                delay = min(delay * 2, STARTUP_MAX_DELAY)

    def _is_sqlite(self) -> bool:
        return "sqlite" in str(self._url).lower()

    def _should_skip_wait(self) -> bool:
        return self._skip_startup_wait or self._is_sqlite()

    def _skip_reason(self) -> str:
        if self._skip_startup_wait:
            return "DB_SKIP_STARTUP_WAIT enabled"
        return "sqlite connection"

    async def _ensure_db_ready(self) -> None:
        if self._db_ready:
            return
        if self._should_skip_wait():
            self._db_ready = True
            if not self._skip_wait_logged:
                system_logger.info(
                    "Skipping DB readiness wait", extra={"reason": self._skip_reason()}
                )
                self._skip_wait_logged = True
            return
        async with self._db_ready_lock:
            if self._db_ready:
                return
            await self._wait_for_db()

    async def init_models(self, *, drop: bool = False) -> None:
        if self._models_initialized and not drop:
            return
        from db.models import Base

        await self._ensure_db_ready()
        try:
            async with self.engine.begin() as conn:
                if drop:
                    await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            self._models_initialized = True
            system_logger.info("DB models initialized")
        except OperationalError:
            system_logger.error("Model init failed", exc_info=True)
            raise

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._models_initialized = False
            self._db_ready = False
            system_logger.info("DB engine disposed")

    @asynccontextmanager
    async def session(self, *, read_only: bool = False) -> AsyncIterator[AsyncSession]:
        await self._ensure_db_ready()
        async with self.session_factory() as session:
            try:
                if read_only:
                    # PostgreSQL-sicher (ignoriert von Sqlite)
                    try:
                        await session.execute(text("SET TRANSACTION READ ONLY"))
                    except Exception:
                        pass
                yield session
                await session.commit()
            except (OperationalError, DBAPIError) as e:
                await session.rollback()
                # Log the specific connection error
                system_logger.error(
                    "Database operation failed - connection error",
                    extra={
                        "error_type": type(e).__name__,
                        "error": str(e),
                        "read_only": read_only,
                    },
                    exc_info=True,
                )
                raise
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def dependency(self) -> AsyncIterator[AsyncSession]:
        async with self.session(read_only=False) as s:
            yield s

    async def readonly_dependency(self) -> AsyncIterator[AsyncSession]:
        async with self.session(read_only=True) as s:
            yield s


db = Database()
