"""Authentication-related domain exceptions."""

from __future__ import annotations

from src.common.domain.exceptions.base import DomainException


class EmailAlreadyRegistered(DomainException):
    pass


class InvalidCredentials(DomainException):
    pass


class InvalidToken(DomainException):
    pass


class SsoAccountUnlinked(DomainException):
    pass


class SsoAccountConflict(DomainException):
    pass


class SsoEmailMismatch(DomainException):
    pass


class PasswordRegistrationDisabled(DomainException):
    pass
