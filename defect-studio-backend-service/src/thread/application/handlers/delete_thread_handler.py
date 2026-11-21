"""Delete thread handler."""

from __future__ import annotations

import logging

from src.common.application.ports.out.gateways import StorageGateway
from src.thread.application.ports.out.repositories import ThreadRepository
from src.thread.application.dto import DeleteThreadInput
from src.thread.application.ports.in_ import DeleteThreadUseCase
from src.thread.domain.exceptions import ThreadNotFound

logger = logging.getLogger(__name__)


class DeleteThreadHandler(DeleteThreadUseCase):
    def __init__(
        self,
        thread_repo: ThreadRepository,
        storage: StorageGateway | None = None,
    ) -> None:
        self._thread_repo = thread_repo
        self._storage = storage

    async def execute(self, inp: DeleteThreadInput) -> None:
        thread = self._thread_repo.find_by_id_and_user(inp.thread_id, inp.user_id)
        if not thread:
            raise ThreadNotFound(f"Thread not found: {inp.thread_id}")
        self._thread_repo.delete(thread)
        if self._storage is None:
            return
        prefixes = [
            f"studio-thumbnails/{thread.id.value}/",
            f"studio-uploads/{thread.id.value}/",
        ]
        agent_tid = (thread.agent_thread_id or "").strip()
        if agent_tid and "/" not in agent_tid:
            prefixes.insert(0, f"threads/{agent_tid}/")
        for prefix in prefixes:
            try:
                for key in self._storage.list_keys(prefix):
                    self._storage.delete(key)
            except Exception:
                logger.warning(
                    "Thread storage cleanup skipped thread_id=%s prefix=%s",
                    thread.id.value,
                    prefix,
                )

