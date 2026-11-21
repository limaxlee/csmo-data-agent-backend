"""PlanId value object (plan context only).

Wraps ``uuid.UUID`` (the internal DB primary key).  The *external*
``plan_id`` string that comes from the agent service is kept as a
plain ``str`` field on ``Plan`` because its type is controlled by an
external system.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.domain.value_objects.base_id import BaseID


@dataclass(frozen=True, eq=False)
class PlanId(BaseID):
    """Identity of a :class:`Plan`."""

