"""Gateway port for password hashing."""

from __future__ import annotations

import abc


class PasswordEncoder(abc.ABC):
    """Port for password hashing."""

    @abc.abstractmethod
    def hash_password(self, password: str) -> str: ...

    @abc.abstractmethod
    def verify_password(self, plain: str, hashed: str) -> bool: ...