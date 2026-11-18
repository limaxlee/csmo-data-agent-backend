"""Mapper: User domain ↔ UserEntity DB."""

from __future__ import annotations

from src.auth.domain.entities import User
from src.auth.infrastructure.entity.user_entity import UserEntity
from src.common.domain.value_objects import UserId


class UserMapper:
    @staticmethod
    def to_domain(entity: UserEntity) -> User:
        return User(
            id=UserId(entity.id), email=entity.email, password_hash=entity.password_hash,
            name=entity.name, role=entity.role, created_at=entity.created_at,
            sso_loginid=entity.sso_loginid,
        )

    @staticmethod
    def to_entity(domain: User) -> UserEntity:
        return UserEntity(
            id=domain.id.value, email=domain.email, password_hash=domain.password_hash,
            name=domain.name, role=domain.role, created_at=domain.created_at,
            sso_loginid=domain.sso_loginid,
        )
