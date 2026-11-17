"""User entity."""

from __future__ import annotations

from datetime import datetime

from src.common.domain.entity import Entity
from src.common.domain.time import utc_now
from src.common.domain.value_objects import UserId


class User(Entity[UserId]):
    """Application user."""

    email: str
    password_hash: str | None
    name: str | None = None
    role: str = "user"
    created_at: datetime | None = None
    sso_loginid: str | None = None

    @staticmethod
    def create(
        email: str, password_hash: str | None, name: str | None = None,
        sso_loginid: str | None = None,
    ) -> User:
        return User(
            id=UserId.generate(),
            email=email,
            password_hash=password_hash,
            name=name,
            role="user",
            created_at=utc_now(),
            sso_loginid=sso_loginid,
        )

    def is_admin(self) -> bool:
        return self.role == "admin"
