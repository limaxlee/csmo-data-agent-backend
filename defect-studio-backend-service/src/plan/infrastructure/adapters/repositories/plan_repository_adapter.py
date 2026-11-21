"""Adapter: implements PlanRepository port using PlanRepositoryImpl."""

from __future__ import annotations

import uuid

from src.plan.application.ports.out.repositories import PlanRepository
from src.plan.domain.entities import Plan
from src.plan.infrastructure.mappers import PlanMapper
from src.plan.infrastructure.repositories.plan_repository_impl import PlanRepositoryImpl


class PlanRepositoryAdapter(PlanRepository):
    def __init__(self, repo: PlanRepositoryImpl) -> None:
        self._repo = repo

    def find_by_thread_and_plan_id(self, thread_id: uuid.UUID, plan_id: str) -> Plan | None:
        entity = self._repo.find_by_thread_and_plan_id(thread_id, plan_id)
        return PlanMapper.to_domain(entity) if entity else None

    def save(self, plan: Plan) -> Plan:
        entity = PlanMapper.to_entity(plan)
        saved = self._repo.save(entity)
        return PlanMapper.to_domain(saved)

    def list_by_thread(self, thread_id: uuid.UUID) -> list[Plan]:
        entities = self._repo.list_by_thread(thread_id)
        return [PlanMapper.to_domain(e) for e in entities]

