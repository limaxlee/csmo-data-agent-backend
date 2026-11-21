"""Thread and Message DTOs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.thread.application.dto import (
    CreateThreadInput,
    ListMessagesOutput,
    ListThreadsOutput,
    MessageOutput,
    ThreadOutput,
    UpdateThreadInput,
)


class ThreadCreateRequest(BaseModel):
    title: str | None = Field(None, max_length=255)

    def to_input(self, user_id: uuid.UUID) -> CreateThreadInput:
        return CreateThreadInput(user_id=user_id, title=self.title)


class ThreadUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

    def to_input(self, user_id: uuid.UUID, thread_id: uuid.UUID) -> UpdateThreadInput:
        return UpdateThreadInput(user_id=user_id, thread_id=thread_id, title=self.title)


class ThreadResponse(BaseModel):
    id: uuid.UUID
    agent_thread_id: str
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    @classmethod
    def from_output(cls, output: ThreadOutput) -> ThreadResponse:
        return cls(
            id=output.id,
            agent_thread_id=output.agent_thread_id,
            title=output.title,
            status=output.status,
            created_at=output.created_at,
            updated_at=output.updated_at,
            message_count=output.message_count,
        )


class ThreadListResponse(BaseModel):
    threads: list[ThreadResponse]
    total: int

    @classmethod
    def from_output(cls, output: ListThreadsOutput) -> ThreadListResponse:
        return cls(
            threads=[ThreadResponse.from_output(t) for t in output.threads],
            total=output.total,
        )


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    metadata: dict[str, Any] | None = None
    created_at: datetime

    @classmethod
    def from_output(cls, output: MessageOutput) -> MessageResponse:
        return cls(
            id=output.id,
            role=output.role,
            content=output.content,
            metadata=output.metadata,
            created_at=output.created_at,
        )


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    total: int

    @classmethod
    def from_output(cls, output: ListMessagesOutput) -> MessageListResponse:
        return cls(
            messages=[MessageResponse.from_output(m) for m in output.messages],
            total=output.total,
        )
