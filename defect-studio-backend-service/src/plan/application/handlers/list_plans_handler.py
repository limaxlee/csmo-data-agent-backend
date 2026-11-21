"""List plans handler."""

from __future__ import annotations

from src.plan.application.ports.out.repositories import PlanRepository
from src.thread.application.ports.out.repositories import ThreadRepository
from src.plan.application.dto import ListPlansInput, ListPlansOutput
from src.plan.application.mappers import PlanMapper
from src.plan.application.ports.in_ import ListPlansUseCase
from src.thread.domain.exceptions import ThreadNotFound


class ListPlansHandler(ListPlansUseCase):
    def __init__(
        self,
        thread_repo: ThreadRepository,
        plan_repo: PlanRepository,
    ) -> None:
        self._thread_repo = thread_repo
        self._plan_repo = plan_repo

    async def execute(self, inp: ListPlansInput) -> ListPlansOutput:
        thread = self._thread_repo.find_by_id_and_user(inp.thread_id, inp.user_id)
        if not thread:
            raise ThreadNotFound(f"Thread not found: {inp.thread_id}")

        plans = self._plan_repo.list_by_thread(thread.id)
        outputs = [PlanMapper.to_output(p) for p in plans]
        return ListPlansOutput(plans=outputs, total=len(outputs))
