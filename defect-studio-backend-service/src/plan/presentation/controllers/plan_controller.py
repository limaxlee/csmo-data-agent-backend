"""Plan controller — view saved defect generation plans."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from src.plan.infrastructure.dependencies import get_get_plan_handler, get_list_plans_handler
from src.auth.domain.entities import User
from src.plan.presentation.dtos.plan_dto import PlanListResponse, PlanResponse
from src.common.presentation.middleware.auth import get_current_user

router = APIRouter(prefix="/api/threads/{thread_id}/plans", tags=["Plans"])


@router.get("", response_model=PlanListResponse)
async def list_plans(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    handler=Depends(get_list_plans_handler),
) -> PlanListResponse:
    """List all plans for a thread."""
    from src.plan.application.dto import ListPlansInput

    output = await handler.execute(
        ListPlansInput(user_id=current_user.id.value, thread_id=thread_id)
    )
    return PlanListResponse.from_output(output)


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    thread_id: uuid.UUID,
    plan_id: str,
    current_user: User = Depends(get_current_user),
    handler=Depends(get_get_plan_handler),
) -> PlanResponse:
    """Get a specific plan."""
    from src.plan.application.dto import GetPlanInput

    output = await handler.execute(
        GetPlanInput(user_id=current_user.id.value, thread_id=thread_id, plan_id=plan_id)
    )
    return PlanResponse.from_output(output)
