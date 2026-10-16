"""Public API for local email-based users."""

from app.core.core_users.dependency import UserManagerDep, get_user_manager
from app.core.core_users.manager import (
    DefaultUserManager,
    InvalidEmailError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserManager,
    normalize_email,
)
from app.core.core_users.model import User
from app.core.core_users.passwords import PasswordHasher, ScryptPasswordHasher

__all__ = [
    "DefaultUserManager",
    "InvalidEmailError",
    "InvalidPasswordError",
    "PasswordHasher",
    "ScryptPasswordHasher",
    "User",
    "UserAlreadyExistsError",
    "UserManager",
    "UserManagerDep",
    "get_user_manager",
    "normalize_email",
]
