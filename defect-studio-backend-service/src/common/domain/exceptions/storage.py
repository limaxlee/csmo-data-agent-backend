"""Storage-related domain exceptions."""

from __future__ import annotations

from src.common.domain.exceptions.base import DomainException


class StorageError(DomainException):
    """Raised when a storage operation (upload/download/delete) fails."""
    pass
