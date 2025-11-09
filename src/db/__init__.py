from __future__ import annotations

from collections.abc import AsyncIterator

from .database import Database, db


async def get_session_dependency() -> AsyncIterator:
    async for s in db.dependency():
        yield s

async def get_readonly_session() -> AsyncIterator:
    async for s in db.readonly_dependency():
        yield s

__all__ = ["Database", "db", "get_session_dependency", "get_readonly_session"]
