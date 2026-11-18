"""RunId value object (Shared Kernel).

Used by: run, result.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.domain.value_objects.base_id import BaseID


@dataclass(frozen=True, eq=False)
class RunId(BaseID):
    """Identity of a :class:`Run`."""
