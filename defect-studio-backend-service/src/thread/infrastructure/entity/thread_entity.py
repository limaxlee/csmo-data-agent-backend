"""Thread and Message ORM models — DB representation only."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.container.database.engine import Base
from src.container.database.db_types import JSONB, UUID


class ThreadEntity(Base):
    __tablename__ = "threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    agent_thread_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["UserEntity"] = relationship("UserEntity", back_populates="threads")  # noqa: F821
    messages: Mapped[list["MessageEntity"]] = relationship(
        "MessageEntity", back_populates="thread", cascade="all, delete-orphan",
        order_by="MessageEntity.created_at",
    )
    runs: Mapped[list["RunEntity"]] = relationship(  # noqa: F821
        "RunEntity", back_populates="thread", cascade="all, delete-orphan"
    )
    plans: Mapped[list["PlanEntity"]] = relationship(  # noqa: F821
        "PlanEntity", back_populates="thread", cascade="all, delete-orphan"
    )


class MessageEntity(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    thread: Mapped["ThreadEntity"] = relationship("ThreadEntity", back_populates="messages")

