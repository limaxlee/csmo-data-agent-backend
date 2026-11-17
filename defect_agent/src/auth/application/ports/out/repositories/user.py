"""Repository port for User."""

from __future__ import annotations

import abc
import uuid

from src.auth.domain.entities import User


class UserRepository(abc.ABC):
    @abc.abstractmethod
    def find_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abc.abstractmethod
    def find_by_email(self, email: str) -> User | None: ...

    def find_by_sso_loginid(self, loginid: str) -> User | None:
        raise NotImplementedError

    def link_sso_loginid(self, user_id: uuid.UUID, loginid: str) -> User:
        raise NotImplementedError

    def provision_sso_user(self, user: User) -> User:
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, user: User) -> User: ...