"""Verified SSO identity passed from the JWT adapter into account use cases."""

from __future__ import annotations

from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email


@dataclass(frozen=True)
class SsoIdentity:
    loginid: str
    email: str | None
    name: str | None


def normalize_email(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.casefold()
    except EmailNotValidError:
        return None