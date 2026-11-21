"""Plan mapper — Plan → PlanOutput."""

from __future__ import annotations

from src.plan.application.dto import PlanOutput
from src.plan.domain.entities import Plan


class PlanMapper:
    @staticmethod
    def to_output(plan: Plan) -> PlanOutput:
        return PlanOutput(
            id=plan.id.value,
            thread_id=plan.thread_id.value,
            plan_id=plan.plan_id,
            content=plan.content,
            status=plan.status,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

