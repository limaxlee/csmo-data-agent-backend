"""Mapper: Plan domain ↔ PlanEntity DB."""

from __future__ import annotations

from src.common.domain.value_objects import ThreadId
from src.plan.domain.entities import Plan
from src.plan.domain.value_objects import PlanId
from src.plan.infrastructure.entity.plan_entity import PlanEntity


class PlanMapper:
    @staticmethod
    def to_domain(entity: PlanEntity) -> Plan:
        return Plan(
            id=PlanId(entity.id), thread_id=ThreadId(entity.thread_id), plan_id=entity.plan_id,
            content=entity.content, status=entity.status,
            created_at=entity.created_at, updated_at=entity.updated_at,
        )

    @staticmethod
    def to_entity(domain: Plan) -> PlanEntity:
        return PlanEntity(
            id=domain.id.value, thread_id=domain.thread_id.value, plan_id=domain.plan_id,
            content=domain.content, status=domain.status,
            created_at=domain.created_at, updated_at=domain.updated_at,
        )
