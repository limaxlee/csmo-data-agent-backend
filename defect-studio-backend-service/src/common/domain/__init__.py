"""Common domain layer.

Exposes the ``Entity`` base class and the Shared Kernel value objects
(``BaseID``, ``UserId``, ``ThreadId``, ``RunId``) that are shared across
multiple bounded contexts.
"""

from src.common.domain.entity import Entity
from src.common.domain.value_objects import (
    BaseID,
    RunId,
    ThreadId,
    UserId,
)

__all__ = [
    "Entity",
    "BaseID",
    "RunId",
    "ThreadId",
    "UserId",
]
