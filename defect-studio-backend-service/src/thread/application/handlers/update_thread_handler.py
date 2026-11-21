"""Update thread handler."""

from __future__ import annotations

from src.thread.application.ports.out.repositories import ThreadRepository
from src.thread.application.dto import ThreadOutput, UpdateThreadInput
from src.thread.application.mappers import ThreadMapper
from src.thread.application.ports.in_ import UpdateThreadUseCase
from src.thread.domain.exceptions import ThreadNotFound


class UpdateThreadHandler(UpdateThreadUseCase):
    def __init__(self, thread_repo: ThreadRepository) -> None:
        self._thread_repo = thread_repo

    async def execute(self, inp: UpdateThreadInput) -> ThreadOutput:
        thread = self._thread_repo.find_by_id_and_user(inp.thread_id, inp.user_id)
        if not thread:
            raise ThreadNotFound(f"Thread not found: {inp.thread_id}")
        thread.rename(inp.title)
        saved = self._thread_repo.save(thread)
        return ThreadMapper.to_output(saved)
