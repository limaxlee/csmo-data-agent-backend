"""MessageId value object (thread context only)."""

from __future__ import annotations

from dataclasses import dataclass

from src.common.domain.value_objects.base_id import BaseID


@dataclass(frozen=True, eq=False)
class MessageId(BaseID):
    """Identity of a :class:`Message`."""