"""List messages handler."""

from __future__ import annotations

from src.thread.application.ports.out.repositories import (
    MessageRepository,
    ThreadRepository,
)
from src.thread.application.dto import ListMessagesInput, ListMessagesOutput
from src.thread.application.mappers import ThreadMapper
from src.thread.application.ports.in_ import ListMessagesUseCase
from src.thread.domain.exceptions import ThreadNotFound


class ListMessagesHandler(ListMessagesUseCase):
    def __init__(
        self,
        thread_repo: ThreadRepository,
        message_repo: MessageRepository,
    ) -> None:
        self._thread_repo = thread_repo
        self._message_repo = message_repo

    async def execute(self, inp: ListMessagesInput) -> ListMessagesOutput:
        thread = self._thread_repo.find_by_id_and_user(inp.thread_id, inp.user_id)
        if not thread:
            raise ThreadNotFound(f"Thread not found: {inp.thread_id}")

        messages, total = self._message_repo.list_by_thread(thread.id, inp.offset, inp.limit)
        msg_outputs = [ThreadMapper.to_message_output(m) for m in messages]
        return ListMessagesOutput(messages=msg_outputs, total=total)

