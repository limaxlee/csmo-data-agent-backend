"""Adapter: implements MessageRepository port using MessageRepositoryImpl."""

from __future__ import annotations

import uuid

from src.thread.application.ports.out.repositories import MessageRepository
from src.thread.domain.entities import Message
from src.thread.infrastructure.mappers import MessageMapper
from src.thread.infrastructure.repositories.message_repository_impl import MessageRepositoryImpl


class MessageRepositoryAdapter(MessageRepository):
    def __init__(self, repo: MessageRepositoryImpl) -> None:
        self._repo = repo

    def save(self, message: Message) -> Message:
        entity = MessageMapper.to_entity(message)
        saved = self._repo.save(entity)
        return MessageMapper.to_domain(saved)

    def list_by_thread(
        self, thread_id: uuid.UUID, offset: int = 0, limit: int = 100,
    ) -> tuple[list[Message], int]:
        entities, total = self._repo.list_by_thread(thread_id, offset, limit)
        return [MessageMapper.to_domain(e) for e in entities], total

