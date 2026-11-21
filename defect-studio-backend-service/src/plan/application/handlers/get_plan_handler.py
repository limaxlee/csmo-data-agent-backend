"""Get plan handler."""

from __future__ import annotations

from src.plan.application.ports.out.repositories import PlanRepository
from src.thread.application.ports.out.repositories import ThreadRepository
from src.plan.application.dto import GetPlanInput, PlanOutput
from src.plan.application.mappers import PlanMapper
from src.plan.application.ports.in_ import GetPlanUseCase
from src.plan.domain.exceptions import PlanNotFound
from src.thread.domain.exceptions import ThreadNotFound


class GetPlanHandler(GetPlanUseCase):
    def __init__(
        self,
        thread_repo: ThreadRepository,
        plan_repo: PlanRepository,
    ) -> None:
        self._thread_repo = thread_repo
        self._plan_repo = plan_repo

    async def execute(self, inp: GetPlanInput) -> PlanOutput:
        thread = self._thread_repo.find_by_id_and_user(inp.thread_id, inp.user_id)
        if not thread:
            raise ThreadNotFound(f"Thread not found: {inp.thread_id}")

        plan = self._plan_repo.find_by_thread_and_plan_id(thread.id, inp.plan_id)
        if not plan:
            raise PlanNotFound(f"Plan not found: {inp.plan_id}")

        return PlanMapper.to_output(plan)

