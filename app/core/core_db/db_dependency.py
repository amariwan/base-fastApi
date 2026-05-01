"""
Primary Dependency for Database Access

`DBSessionDep` provides a FastAPI-compatible dependency that yields an
`AsyncSession` from the application's async SQLAlchemy session manager.

Usage:
    - Inject `DBSessionDep` into your path operations or other dependencies
      to perform async database queries.
    - Ensures proper session lifecycle: rollback on exception and closure
      are handled automatically. Commits must be performed explicitly by the caller.

Example:
    router = APIRouter()

    @router.get("/users/{user_id}")
    async def get_user(user_id: int, db: AsyncSession = DBSessionDep):
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user

Notes:
    - This is the single recommended entry point for obtaining a database session
      in the application.
    - Internally, it uses `get_db_session` from the async DB session manager.
"""

from typing import Annotated

from app.core.core_db.async_db_session_maker import get_db_session
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Annotated type alias for injecting an AsyncSession via FastAPI's Depends mechanism.
DBSessionDep = Annotated[AsyncSession, Depends(dependency=get_db_session)]
