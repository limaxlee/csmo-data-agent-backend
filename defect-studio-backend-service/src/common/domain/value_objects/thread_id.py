"""ThreadId value object (Shared Kernel).

Used by: thread, run, plan, train_data, result.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.domain.value_objects.base_id import BaseID


@dataclass(frozen=True, eq=False)
class ThreadId(BaseID):
    """Identity of a :class:`Thread`."""
