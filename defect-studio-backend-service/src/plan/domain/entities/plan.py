"""Plan entity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.common.domain.entity import Entity
from src.common.domain.time import utc_now
from src.common.domain.value_objects import ThreadId
from src.plan.domain.value_objects import PlanId
from src.plan.domain.value_objects import PlanStatus


class Plan(Entity[PlanId]):
    """A defect generation plan."""

    thread_id: ThreadId
    plan_id: str  # external ID from agent service
    content: dict[str, Any]
    status: str = PlanStatus.DRAFT.value
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def advance_status(self, status: str) -> bool:
        """Move the plan to *status* if that is forward. Returns whether it moved.

        Every source of a plan's status is a replay risk. The agent re-sends
        ``plan.updated`` after a plan has already run, and its payload carries no
        status at all — so the caller's default lands on the row and an executed
        plan reads as a draft again. A run's event buffer replays wholesale when
        a consumer reconnects, sending ``infer.started`` after ``infer.completed``
        has already been seen.

        Refusing to go backwards makes all of those harmless without asking any
        caller to know which case it is in.
        """
        if PlanStatus.rank_of(status) <= PlanStatus.rank_of(self.status):
            return False
        self.status = status
        self.updated_at = utc_now()
        return True

    @staticmethod
    def create(
        thread_id: ThreadId,
        plan_id: str,
        content: dict[str, Any],
        status: str = PlanStatus.DRAFT.value,
    ) -> Plan:
        now = utc_now()
        return Plan(
            id=PlanId.generate(),
            thread_id=thread_id,
            plan_id=plan_id,
            content=content,
            status=status,
            created_at=now,
            updated_at=now,
        )
