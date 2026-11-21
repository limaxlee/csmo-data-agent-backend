"""Repository port for Plan."""

from __future__ import annotations

import abc
import uuid

from src.plan.domain.entities import Plan


class PlanRepository(abc.ABC):
    @abc.abstractmethod
    def find_by_thread_and_plan_id(self, thread_id: uuid.UUID, plan_id: str) -> Plan | None: ...

    @abc.abstractmethod
    def save(self, plan: Plan) -> Plan: ...

    @abc.abstractmethod
    def list_by_thread(self, thread_id: uuid.UUID) -> list[Plan]: ...
