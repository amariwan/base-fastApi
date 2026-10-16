"""Extensible application service for local email-based users."""

from __future__ import annotations

from uuid import UUID

from app.core.core_users.model import User
from app.core.core_users.passwords import PasswordHasher, ScryptPasswordHasher
from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class InvalidEmailError(ValueError):
    pass


class InvalidPasswordError(ValueError):
    pass


class UserAlreadyExistsError(ValueError):
    pass


def normalize_email(email: str) -> str:
    try:
        result = validate_email(email.strip(), check_deliverability=False)
    except EmailNotValidError as exc:
        raise InvalidEmailError("A valid email address is required") from exc
    return result.normalized.casefold()


class UserManager[UserT: User]:
    """Email-first user operations with overridable validation and lifecycle hooks.

    The manager flushes changes but never commits. The calling use case owns the
    transaction so user creation can remain atomic with adjacent business work.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        user_model: type[UserT],
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        self._session = session
        self._user_model = user_model
        self._password_hasher = password_hasher or ScryptPasswordHasher()

    async def get(self, user_id: UUID) -> UserT | None:
        return await self._session.get(self._user_model, user_id)

    async def get_by_email(self, email: str) -> UserT | None:
        normalized = normalize_email(email)
        result = await self._session.execute(select(self._user_model).where(self._user_model.email == normalized))
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        password: str,
        *,
        is_verified: bool = False,
        is_superuser: bool = False,
    ) -> UserT:
        normalized = normalize_email(email)
        await self.validate_password(password)
        if await self.get_by_email(normalized) is not None:
            raise UserAlreadyExistsError(normalized)

        user = self._user_model(
            email=normalized,
            hashed_password=self._password_hasher.hash(password),
            is_verified=is_verified,
            is_superuser=is_superuser,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(user)
                await self._session.flush()
        except IntegrityError as exc:
            raise UserAlreadyExistsError(normalized) from exc
        await self._session.refresh(user)
        await self.on_after_register(user)
        return user

    async def authenticate(self, email: str, password: str) -> UserT | None:
        try:
            user = await self.get_by_email(email)
        except InvalidEmailError:
            return None
        if user is None or not user.is_active:
            return None
        if not self._password_hasher.verify(password, user.hashed_password):
            return None
        return user

    async def set_password(self, user: UserT, password: str) -> None:
        await self.validate_password(password)
        user.hashed_password = self._password_hasher.hash(password)
        await self._session.flush()
        await self.on_after_update(user)

    async def validate_password(self, password: str) -> None:
        if len(password) < 12:
            raise InvalidPasswordError("Password must contain at least 12 characters")

    async def on_after_register(self, user: UserT) -> None:
        """Override for audit events or verification mail orchestration."""

    async def on_after_update(self, user: UserT) -> None:
        """Override for audit events after a user mutation."""


class DefaultUserManager(UserManager[User]):
    def __init__(self, session: AsyncSession, *, password_hasher: PasswordHasher | None = None) -> None:
        super().__init__(session, user_model=User, password_hasher=password_hasher)


__all__ = [
    "DefaultUserManager",
    "InvalidEmailError",
    "InvalidPasswordError",
    "UserAlreadyExistsError",
    "UserManager",
    "normalize_email",
]
