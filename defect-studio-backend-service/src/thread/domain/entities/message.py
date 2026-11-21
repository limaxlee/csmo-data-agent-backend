"""Message entity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.common.domain.entity import Entity
from src.common.domain.time import utc_now
from src.common.domain.value_objects import ThreadId
from src.thread.domain.value_objects import MessageId


class Message(Entity[MessageId]):
    """A single message in a conversation thread."""

    thread_id: ThreadId
    role: str  # user, assistant, system
    content: str
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None

    @staticmethod
    def create(
        thread_id: ThreadId,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        return Message(
            id=MessageId.generate(),
            thread_id=thread_id,
            role=role,
            content=content,
            metadata=metadata,
            created_at=utc_now(),
        )

