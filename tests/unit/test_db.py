from __future__ import annotations

import pytest
from sqlalchemy import text

from db import Database, db, get_readonly_session, get_session_dependency
from db.dsn import build_url, masked, ssl_context


def test_build_url_and_mask(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@host/db")
    url = build_url()
    assert "postgresql+asyncpg" in str(url)
    assert masked(url).startswith("postgresql+asyncpg://****:****@")


def test_ssl_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_SSL", "true")
    monkeypatch.setenv("DB_SSL_NO_VERIFY", "true")
    ctx = ssl_context()
    assert ctx is not None and ctx.check_hostname is False


@pytest.mark.asyncio
async def test_database_session_sqlite(tmp_path) -> None:
    database = Database(url=f"sqlite+aiosqlite:///{tmp_path}/test.db")
    await database.init_models()
    async with database.session(read_only=True) as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    await database.dispose()


@pytest.mark.asyncio
async def test_get_session_dependency_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_dependency():
        yield "session"

    async def fake_readonly():
        yield "readonly"

    monkeypatch.setattr(db, "dependency", fake_dependency)
    monkeypatch.setattr(db, "readonly_dependency", fake_readonly)

    sessions = []
    async for session in get_session_dependency():
        sessions.append(session)
    assert sessions == ["session"]

    readonly_sessions = []
    async for session in get_readonly_session():
        readonly_sessions.append(session)
    assert readonly_sessions == ["readonly"]
