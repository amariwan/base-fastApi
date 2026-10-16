"""Database model for local email-based identities."""

from __future__ import annotations

from app.core.core_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Core local user. Services may reference its UUID, not this ORM model."""

    __tablename__ = "core_users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


__all__ = ["User"]
