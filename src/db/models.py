from __future__ import annotations

"""Declarative base used by Alembic and the Database helper."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Application-wide declarative base."""

    pass


__all__ = ["Base"]

