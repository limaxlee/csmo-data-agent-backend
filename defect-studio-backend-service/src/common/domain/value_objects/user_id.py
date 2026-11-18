"""UserId value object (Shared Kernel).

Used by: auth, thread, run, train_data.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.domain.value_objects.base_id import BaseID


@dataclass(frozen=True, eq=False)
class UserId(BaseID):
    """Identity of a :class:`User`."""
