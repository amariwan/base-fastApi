"""FastAPI dependency for the default user manager."""

from typing import Annotated

from app.core.core_db import DBSessionDep
from app.core.core_users.manager import DefaultUserManager
from fastapi import Depends


def get_user_manager(session: DBSessionDep) -> DefaultUserManager:
    return DefaultUserManager(session)


UserManagerDep = Annotated[DefaultUserManager, Depends(get_user_manager)]

__all__ = ["UserManagerDep", "get_user_manager"]
