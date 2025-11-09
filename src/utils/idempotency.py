from __future__ import annotations

"""Helpers for idempotent writes."""

from typing import Protocol, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SupportsIdempotencyKey(Protocol):
    idempotency_key: str


ModelT = TypeVar("ModelT", bound=SupportsIdempotencyKey)


async def find_by_idempotency(
    session: AsyncSession, model: type[ModelT], key: str
) -> ModelT | None:
    """Return an existing model instance matching the idempotency key."""
    if not key:
        return None
    stmt = select(model).where(model.idempotency_key == key)  # type: ignore[attr-defined]
    result = await session.execute(stmt)
    return result.scalars().first()


__all__ = ["find_by_idempotency", "SupportsIdempotencyKey"]

