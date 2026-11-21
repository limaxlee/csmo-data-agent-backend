"""Plan Context — DI providers for repository adapters and use case handlers."""

from __future__ import annotations

from fastapi import Depends

from src.plan.application.handlers import GetPlanHandler, ListPlansHandler
from src.plan.infrastructure.adapters.repositories.plan_repository_adapter import PlanRepositoryAdapter
from src.plan.infrastructure.repositories.plan_repository_impl import PlanRepositoryImpl
from src.thread.infrastructure.adapters.repositories.thread_repository_adapter import ThreadRepositoryAdapter
from src.container.database.engine import get_db
from src.container.infrastructure import get_thread_repo_adapter


# ── Repository Adapter ──

def get_plan_repo_adapter(db=Depends(get_db)) -> PlanRepositoryAdapter:
    return PlanRepositoryAdapter(PlanRepositoryImpl(db))


# ── Handlers ──

def get_list_plans_handler(
    thread_repo: ThreadRepositoryAdapter = Depends(get_thread_repo_adapter),
    plan_repo: PlanRepositoryAdapter = Depends(get_plan_repo_adapter),
) -> ListPlansHandler:
    return ListPlansHandler(thread_repo, plan_repo)


def get_get_plan_handler(
    thread_repo: ThreadRepositoryAdapter = Depends(get_thread_repo_adapter),
    plan_repo: PlanRepositoryAdapter = Depends(get_plan_repo_adapter),
) -> GetPlanHandler:
    return GetPlanHandler(thread_repo, plan_repo)

