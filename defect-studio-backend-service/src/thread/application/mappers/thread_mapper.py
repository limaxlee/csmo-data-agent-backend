"""Thread mapper — Thread → ThreadOutput, Message → MessageOutput."""

from __future__ import annotations

from src.thread.application.dto import (
    MessageOutput,
    ThreadOutput,
)
from src.thread.domain.entities import (
    Message,
    Thread,
)


class ThreadMapper:
    @staticmethod
    def to_output(thread: Thread, message_count: int = 0) -> ThreadOutput:
        return ThreadOutput(
            id=thread.id.value,
            user_id=thread.user_id.value,
            agent_thread_id=thread.agent_thread_id,
            title=thread.title,
            status=thread.status,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            message_count=message_count,
        )

    @staticmethod
    def to_message_output(message: Message) -> MessageOutput:
        return MessageOutput(
            id=message.id.value,
            thread_id=message.thread_id.value,
            role=message.role,
            content=message.content,
            metadata=message.metadata,
            created_at=message.created_at,
        )

