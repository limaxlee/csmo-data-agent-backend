"""Plan UseCase interfaces (driving ports)."""

from __future__ import annotations

import abc

from src.plan.application.dto.plan import GetPlanInput, ListPlansInput, ListPlansOutput, PlanOutput


class ListPlansUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: ListPlansInput) -> ListPlansOutput: ...


class GetPlanUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: GetPlanInput) -> PlanOutput: ...

