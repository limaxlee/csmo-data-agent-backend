"""Thread entity."""

from __future__ import annotations

from datetime import datetime

from src.common.domain.entity import Entity
from src.common.domain.time import utc_now
from src.common.domain.value_objects import ThreadId, UserId
from src.thread.domain.value_objects import ThreadStatus


class Thread(Entity[ThreadId]):
    """A conversation thread (maps to agent_service thread_id)."""

    user_id: UserId
    agent_thread_id: str
    title: str | None = None
    status: str = ThreadStatus.ACTIVE.value
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def create(user_id: UserId, agent_thread_id: str, title: str | None = None) -> Thread:
        now = utc_now()
        return Thread(
            id=ThreadId.generate(),
            user_id=user_id,
            agent_thread_id=agent_thread_id,
            title=title,
            status=ThreadStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
        )

    def rename(self, title: str) -> None:
        self.title = title
        self.updated_at = utc_now()

