"""Gateway port for JWT token creation and verification."""

from __future__ import annotations

import abc
import uuid
from typing import Any


class TokenProvider(abc.ABC):
    """Port for JWT token creation and verification."""

    @abc.abstractmethod
    def create_access_token(self, subject: uuid.UUID, extra_claims: dict[str, Any] | None = None) -> str: ...

    @abc.abstractmethod
    def create_refresh_token(self, subject: uuid.UUID) -> str: ...

    @abc.abstractmethod
    def decode_token(self, token: str) -> dict[str, Any]: ...