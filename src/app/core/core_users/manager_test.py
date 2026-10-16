from collections.abc import AsyncIterator

import pytest
from app.core.core_db import Base
from app.core.core_users import DefaultUserManager, InvalidPasswordError, ScryptPasswordHasher, User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
async def user_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def test_user_manager_creates_and_authenticates_by_normalized_email(user_session: AsyncSession) -> None:
    manager = DefaultUserManager(user_session)

    user = await manager.create(" Person@Example.COM ", "correct horse battery staple")

    assert user.email == "person@example.com"
    assert user.hashed_password != "correct horse battery staple"
    assert await manager.authenticate("PERSON@example.com", "correct horse battery staple") is user
    assert await manager.authenticate("person@example.com", "wrong password") is None


async def test_user_manager_rejects_short_password(user_session: AsyncSession) -> None:
    manager = DefaultUserManager(user_session)

    with pytest.raises(InvalidPasswordError):
        await manager.create("person@example.com", "short")


async def test_user_manager_does_not_authenticate_inactive_user(user_session: AsyncSession) -> None:
    manager = DefaultUserManager(user_session)
    user = await manager.create("person@example.com", "correct horse battery staple")
    user.is_active = False
    await user_session.flush()

    assert await manager.authenticate(user.email, "correct horse battery staple") is None


def test_user_model_is_registered_on_core_metadata() -> None:
    assert User.__table__ is Base.metadata.tables["core_users"]


def test_password_hasher_rejects_unsafe_or_malformed_parameters() -> None:
    hasher = ScryptPasswordHasher()

    assert hasher.verify("password", "scrypt$999999999$8$1$c2FsdA==$ZGlnZXN0") is False
    assert hasher.verify("password", "not-a-hash") is False
