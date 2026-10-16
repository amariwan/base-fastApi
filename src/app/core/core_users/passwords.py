"""Password hashing contract and a dependency-free scrypt implementation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, encoded_hash: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class ScryptPasswordHasher:
    """Versioned scrypt hashes suitable for storage in ``User.hashed_password``."""

    n: int = 2**14
    r: int = 8
    p: int = 1
    salt_bytes: int = 16
    key_bytes: int = 64

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(self.salt_bytes)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=self.n,
            r=self.r,
            p=self.p,
            dklen=self.key_bytes,
        )
        return "$".join(
            (
                "scrypt",
                str(self.n),
                str(self.r),
                str(self.p),
                base64.urlsafe_b64encode(salt).decode("ascii"),
                base64.urlsafe_b64encode(digest).decode("ascii"),
            )
        )

    def verify(self, password: str, encoded_hash: str) -> bool:
        try:
            algorithm, raw_n, raw_r, raw_p, raw_salt, raw_digest = encoded_hash.split("$", maxsplit=5)
            if algorithm != "scrypt":
                return False
            n, r, p = int(raw_n), int(raw_r), int(raw_p)
            salt = base64.urlsafe_b64decode(raw_salt.encode("ascii"))
            expected = base64.urlsafe_b64decode(raw_digest.encode("ascii"))
            if n < 2**12 or n > 2**18 or n & (n - 1) or not 1 <= r <= 16 or not 1 <= p <= 4:
                return False
            if not 8 <= len(salt) <= 64 or not 32 <= len(expected) <= 128:
                return False
            actual = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=n,
                r=r,
                p=p,
                dklen=len(expected),
            )
        except (MemoryError, TypeError, ValueError):
            return False
        return hmac.compare_digest(actual, expected)


__all__ = ["PasswordHasher", "ScryptPasswordHasher"]
