"""Repository ports for Thread and Message."""

from __future__ import annotations

import abc
import uuid

from src.thread.domain.entities import (
    Message,
    Thread,
)


class ThreadRepository(abc.ABC):
    @abc.abstractmethod
    def find_by_id_and_user(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> Thread | None: ...

    @abc.abstractmethod
    def find_by_agent_thread_id(self, agent_thread_id: str, user_id: uuid.UUID) -> Thread | None: ...

    @abc.abstractmethod
    def save(self, thread: Thread) -> Thread: ...

    @abc.abstractmethod
    def delete(self, thread: Thread) -> None: ...

    @abc.abstractmethod
    def list_by_user(
        self, user_id: uuid.UUID, offset: int = 0, limit: int = 50,
    ) -> tuple[list[tuple[Thread, int]], int]:
        """Return (list of (thread, message_count), total_count)."""
        ...


class MessageRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, message: Message) -> Message: ...

    @abc.abstractmethod
    def list_by_thread(
        self, thread_id: uuid.UUID, offset: int = 0, limit: int = 100,
    ) -> tuple[list[Message], int]:
        """Return (messages, total_count)."""
        ...

