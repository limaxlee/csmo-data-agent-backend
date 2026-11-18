"""User ORM model — DB representation only."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.container.database.engine import Base
from src.container.database.db_types import UUID


class UserEntity(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sso_loginid: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    threads: Mapped[list["ThreadEntity"]] = relationship(  # noqa: F821
        "ThreadEntity", back_populates="user", cascade="all, delete-orphan"
    )


class SsoLinkAuditEntity(Base):
    """Immutable record of SSO identity attachment or account provisioning."""

    __tablename__ = "sso_link_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    sso_loginid: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
