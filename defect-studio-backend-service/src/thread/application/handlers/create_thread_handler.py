"""Create thread handler."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from src.thread.application.ports.out.repositories import ThreadRepository
from src.thread.application.dto import CreateThreadInput, ThreadOutput
from src.thread.application.mappers import ThreadMapper
from src.thread.application.ports.in_ import CreateThreadUseCase
from src.thread.domain.entities import Thread

# Korea does not observe DST, so a fixed offset is always correct for KST.
_KST = timezone(timedelta(hours=9))
_DEFAULT_TITLE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _default_title() -> str:
    """Default title: KST creation timestamp, e.g. '2026-10-27 23:15:42'."""
    return datetime.now(_KST).strftime(_DEFAULT_TITLE_FORMAT)


class CreateThreadHandler(CreateThreadUseCase):
    def __init__(self, thread_repo: ThreadRepository) -> None:
        self._thread_repo = thread_repo

    async def execute(self, inp: CreateThreadInput) -> ThreadOutput:
        agent_thread_id = f"{str(inp.user_id)[:8]}_{uuid.uuid4().hex[:12]}"
        title = inp.title if inp.title and inp.title.strip() else _default_title()
        thread = Thread.create(
            user_id=inp.user_id,
            agent_thread_id=agent_thread_id,
            title=title,
        )
        saved = self._thread_repo.save(thread)
        return ThreadMapper.to_output(saved)

