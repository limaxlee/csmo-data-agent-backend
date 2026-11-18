"""Shared Kernel value objects.

This package holds value objects shared across multiple bounded contexts
(Shared Kernel pattern).  Only IDs that are referenced by **more than one**
context live here.  IDs that belong to a single context should be defined
within that context's own ``domain/value_objects/`` package.
"""

from src.common.domain.value_objects.base_id import BaseID
from src.common.domain.value_objects.run_id import RunId
from src.common.domain.value_objects.thread_id import ThreadId
from src.common.domain.value_objects.user_id import UserId

__all__ = [
    "BaseID",
    "RunId",
    "ThreadId",
    "UserId",
]
