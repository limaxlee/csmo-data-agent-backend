"""List threads handler."""

from __future__ import annotations

from src.thread.application.ports.out.repositories import ThreadRepository
from src.thread.application.dto import ListThreadsInput, ListThreadsOutput
from src.thread.application.mappers import ThreadMapper
from src.thread.application.ports.in_ import ListThreadsUseCase


class ListThreadsHandler(ListThreadsUseCase):
    def __init__(self, thread_repo: ThreadRepository) -> None:
        self._thread_repo = thread_repo

    async def execute(self, inp: ListThreadsInput) -> ListThreadsOutput:
        results, total = self._thread_repo.list_by_user(inp.user_id, inp.offset, inp.limit)
        threads = [ThreadMapper.to_output(t, msg_count) for t, msg_count in results]
        return ListThreadsOutput(threads=threads, total=total)

