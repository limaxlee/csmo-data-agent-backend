"""Get thread handler."""

from __future__ import annotations

from src.thread.application.ports.out.repositories import ThreadRepository
from src.thread.application.dto import GetThreadInput, ThreadOutput
from src.thread.application.mappers import ThreadMapper
from src.thread.application.ports.in_ import GetThreadUseCase
from src.thread.domain.exceptions import ThreadNotFound


class GetThreadHandler(GetThreadUseCase):
    def __init__(self, thread_repo: ThreadRepository) -> None:
        self._thread_repo = thread_repo

    async def execute(self, inp: GetThreadInput) -> ThreadOutput:
        thread = self._thread_repo.find_by_id_and_user(inp.thread_id, inp.user_id)
        if not thread:
            raise ThreadNotFound(f"Thread not found: {inp.thread_id}")
        return ThreadMapper.to_output(thread)

