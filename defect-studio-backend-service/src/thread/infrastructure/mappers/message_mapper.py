"""Mapper: Message domain ↔ MessageEntity DB."""

from __future__ import annotations

from src.common.domain.value_objects import ThreadId
from src.thread.domain.entities import Message
from src.thread.domain.value_objects import MessageId
from src.thread.infrastructure.entity.thread_entity import MessageEntity


class MessageMapper:
    @staticmethod
    def to_domain(entity: MessageEntity) -> Message:
        return Message(
            id=MessageId(entity.id), thread_id=ThreadId(entity.thread_id),
            role=entity.role,
            content=entity.content, metadata=entity.metadata_, created_at=entity.created_at,
        )

    @staticmethod
    def to_entity(domain: Message) -> MessageEntity:
        return MessageEntity(
            id=domain.id.value, thread_id=domain.thread_id.value,
            role=domain.role,
            content=domain.content, metadata_=domain.metadata, created_at=domain.created_at,
        )

