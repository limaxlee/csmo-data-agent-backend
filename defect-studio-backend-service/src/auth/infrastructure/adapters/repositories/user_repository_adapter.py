"""Adapter: implements UserRepository port using UserRepositoryImpl."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError

from src.auth.domain.exceptions import EmailAlreadyRegistered, InvalidToken, SsoAccountConflict

from src.auth.application.ports.out.repositories import UserRepository
from src.auth.domain.entities import User
from src.auth.infrastructure.mappers import UserMapper
from src.auth.infrastructure.repositories.user_repository_impl import UserRepositoryImpl

_PG_UNIQUE_VIOLATION = "23505"


def _is_unique_violation(exc: IntegrityError) -> bool:
    """True for a duplicate key; False for foreign key, NOT NULL and other violations."""
    if getattr(exc.orig, "pgcode", None) == _PG_UNIQUE_VIOLATION:
        return True
    return "UNIQUE constraint failed" in str(exc.orig)  # SQLite


class UserRepositoryAdapter(UserRepository):
    def __init__(self, repo: UserRepositoryImpl) -> None:
        self._repo = repo

    def find_by_id(self, user_id: uuid.UUID) -> User | None:
        entity = self._repo.find_by_id(user_id)
        return UserMapper.to_domain(entity) if entity else None

    def find_by_email(self, email: str) -> User | None:
        entity = self._repo.find_by_email(email)
        return UserMapper.to_domain(entity) if entity else None

    def find_by_sso_loginid(self, loginid: str) -> User | None:
        entity = self._repo.find_by_sso_loginid(loginid)
        return UserMapper.to_domain(entity) if entity else None

    def link_sso_loginid(self, user_id: uuid.UUID, loginid: str) -> User:
        try:
            entity = self._repo.link_sso_loginid(user_id, loginid)
        except IntegrityError as exc:
            self._repo.rollback()
            if not _is_unique_violation(exc):
                raise
            raise SsoAccountConflict("SSO identity is linked to another account") from exc
        if entity is None:
            raise InvalidToken("Account no longer exists")
        if entity.sso_loginid != loginid:
            raise SsoAccountConflict("Local account is linked to another SSO identity")
        return UserMapper.to_domain(entity)

    def provision_sso_user(self, user: User) -> User:
        try:
            entity = self._repo.provision_sso_user(UserMapper.to_entity(user))
            return UserMapper.to_domain(entity)
        except IntegrityError as exc:
            self._repo.rollback()
            if not _is_unique_violation(exc):
                raise
            # Concurrent provisioning of the same SSO identity is idempotent.
            mapped = self.find_by_sso_loginid(user.sso_loginid)
            if mapped:
                return mapped
            raise SsoAccountConflict("SSO account conflicts with an existing user") from exc

    def save(self, user: User) -> User:
        entity = UserMapper.to_entity(user)
        try:
            saved = self._repo.save(entity)
        except IntegrityError as exc:
            self._repo.rollback()
            if not _is_unique_violation(exc):
                raise
            raise EmailAlreadyRegistered("Email already registered") from exc
        return UserMapper.to_domain(saved)
