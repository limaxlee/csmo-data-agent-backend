"""Plan DTOs — Input/Output dataclasses for plan use cases."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class PlanOutput:
    id: uuid.UUID
    thread_id: uuid.UUID
    plan_id: str
    content: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ListPlansInput:
    user_id: uuid.UUID
    thread_id: uuid.UUID


@dataclass
class ListPlansOutput:
    plans: list[PlanOutput]
    total: int


@dataclass
class GetPlanInput:
    user_id: uuid.UUID
    thread_id: uuid.UUID
    plan_id: str
