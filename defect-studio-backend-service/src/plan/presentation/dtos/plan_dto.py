"""Plan DTOs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from src.plan.application.dto import (
    ListPlansOutput,
    PlanOutput,
)


class PlanResponse(BaseModel):
    id: uuid.UUID
    plan_id: str
    content: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_output(cls, output: PlanOutput) -> PlanResponse:
        return cls(
            id=output.id,
            plan_id=output.plan_id,
            content=output.content,
            status=output.status,
            created_at=output.created_at,
            updated_at=output.updated_at,
        )


class PlanListResponse(BaseModel):
    plans: list[PlanResponse]
    total: int

    @classmethod
    def from_output(cls, output: ListPlansOutput) -> PlanListResponse:
        return cls(
            plans=[PlanResponse.from_output(p) for p in output.plans],
            total=output.total,
        )
