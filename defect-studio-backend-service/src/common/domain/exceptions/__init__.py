"""Common domain exceptions."""

from src.common.domain.exceptions.base import DomainException
from src.common.domain.exceptions.storage import StorageError

__all__ = ["DomainException", "StorageError"]
