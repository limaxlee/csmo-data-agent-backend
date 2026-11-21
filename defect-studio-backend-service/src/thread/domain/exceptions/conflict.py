"""Thread deletion conflict exception."""

from src.common.domain.exceptions import DomainException


class ThreadDeletionConflict(DomainException):
    """Raised when a thread cannot be deleted due to active uploads or runs."""

    def __init__(self, message: str, *, code: str = "thread_deletion_conflict") -> None:
        super().__init__(message)
        self.code = code

