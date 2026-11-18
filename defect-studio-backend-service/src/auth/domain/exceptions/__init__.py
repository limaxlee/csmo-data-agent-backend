"""Auth domain exceptions."""

from src.auth.domain.exceptions.auth import (
    EmailAlreadyRegistered, InvalidCredentials, InvalidToken,
    PasswordRegistrationDisabled, SsoAccountConflict, SsoAccountUnlinked,
    SsoEmailMismatch,
)
from src.auth.domain.exceptions.not_found import UserNotFound

__all__ = [
    "EmailAlreadyRegistered", "InvalidCredentials", "InvalidToken", "UserNotFound",
    "PasswordRegistrationDisabled", "SsoAccountConflict", "SsoAccountUnlinked",
    "SsoEmailMismatch",
]