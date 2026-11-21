"""Plan ORM model — DB representation only."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.container.database.engine import Base
from src.container.database.db_types import JSONB, UUID


class PlanEntity(Base):
    __tablename__ = "plans"

    __table_args__ = (
        # ``id`` is a surrogate; what identifies a plan is the pair the agent
        # uses to name it. Without this, RunEventRecorder._save_plan's
        # look-then-upsert can leave a thread holding two rows for plan "0",
        # and nothing downstream could say which one is the plan. It is also
        # what result_artifacts' composite foreign key references — Postgres
        # requires a unique index on the referenced columns.
        UniqueConstraint("thread_id", "plan_id", name="uq_plans_thread_plan"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    thread: Mapped["ThreadEntity"] = relationship("ThreadEntity", back_populates="plans")  # noqa: F821
