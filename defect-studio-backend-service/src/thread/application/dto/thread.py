"""Thread DTOs — Input/Output dataclasses for thread use cases."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ThreadOutput:
    id: uuid.UUID
    user_id: uuid.UUID
    agent_thread_id: str
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


@dataclass
class CreateThreadInput:
    user_id: uuid.UUID
    title: str | None = None


@dataclass
class ListThreadsInput:
    user_id: uuid.UUID
    offset: int = 0
    limit: int = 50


@dataclass
class ListThreadsOutput:
    threads: list[ThreadOutput]
    total: int


@dataclass
class GetThreadInput:
    user_id: uuid.UUID
    thread_id: uuid.UUID


@dataclass
class UpdateThreadInput:
    user_id: uuid.UUID
    thread_id: uuid.UUID
    title: str


@dataclass
class DeleteThreadInput:
    user_id: uuid.UUID
    thread_id: uuid.UUID


@dataclass
class MessageOutput:
    id: uuid.UUID
    thread_id: uuid.UUID
    role: str
    content: str
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None


@dataclass
class ListMessagesInput:
    user_id: uuid.UUID
    thread_id: uuid.UUID
    offset: int = 0
    limit: int = 100


@dataclass
class ListMessagesOutput:
    messages: list[MessageOutput]
    total: int
