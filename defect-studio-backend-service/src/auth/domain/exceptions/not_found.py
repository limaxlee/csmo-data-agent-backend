"""Auth not-found exceptions."""

from __future__ import annotations

from src.common.domain.exceptions.base import DomainException


class UserNotFound(DomainException):
    pass
