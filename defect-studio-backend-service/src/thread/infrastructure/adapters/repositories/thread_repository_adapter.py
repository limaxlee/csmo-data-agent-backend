"""Adapter: implements ThreadRepository port using ThreadRepositoryImpl."""

from __future__ import annotations

import uuid

from src.thread.application.ports.out.repositories import ThreadRepository
from src.thread.domain.entities import Thread
from src.thread.infrastructure.mappers import ThreadMapper
from src.thread.infrastructure.repositories.thread_repository_impl import ThreadRepositoryImpl


class ThreadRepositoryAdapter(ThreadRepository):
    def __init__(self, repo: ThreadRepositoryImpl) -> None:
        self._repo = repo

    def find_by_id_and_user(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> Thread | None:
        entity = self._repo.find_by_id_and_user(thread_id, user_id)
        return ThreadMapper.to_domain(entity) if entity else None

    def find_by_agent_thread_id(self, agent_thread_id: str, user_id: uuid.UUID) -> Thread | None:
        entity = self._repo.find_by_agent_thread_id(agent_thread_id, user_id)
        return ThreadMapper.to_domain(entity) if entity else None

    def save(self, thread: Thread) -> Thread:
        entity = ThreadMapper.to_entity(thread)
        saved = self._repo.save(entity)
        return ThreadMapper.to_domain(saved)

    def delete(self, thread: Thread) -> None:
        entity = ThreadMapper.to_entity(thread)
        self._repo.delete(entity)

    def list_by_user(
        self, user_id: uuid.UUID, offset: int = 0, limit: int = 50,
    ) -> tuple[list[tuple[Thread, int]], int]:
        results, total = self._repo.list_by_user(user_id, offset, limit)
        return [(ThreadMapper.to_domain(entity), msg_count) for entity, msg_count in results], total

