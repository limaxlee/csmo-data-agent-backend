"""Mapper: Thread domain ↔ ThreadEntity DB."""

from __future__ import annotations

from src.common.domain.value_objects import ThreadId, UserId
from src.thread.domain.entities import Thread
from src.thread.infrastructure.entity.thread_entity import ThreadEntity


class ThreadMapper:
    @staticmethod
    def to_domain(entity: ThreadEntity) -> Thread:
        return Thread(
            id=ThreadId(entity.id), user_id=UserId(entity.user_id),
            agent_thread_id=entity.agent_thread_id,
            title=entity.title, status=entity.status,
            created_at=entity.created_at, updated_at=entity.updated_at,
        )

    @staticmethod
    def to_entity(domain: Thread) -> ThreadEntity:
        return ThreadEntity(
            id=domain.id.value, user_id=domain.user_id.value,
            agent_thread_id=domain.agent_thread_id,
            title=domain.title, status=domain.status,
            created_at=domain.created_at, updated_at=domain.updated_at,
        )

