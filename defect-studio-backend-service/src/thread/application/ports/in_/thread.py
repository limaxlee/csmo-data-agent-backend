"""Thread UseCase interfaces (driving ports)."""

from __future__ import annotations

import abc

from src.thread.application.dto.thread import (
    CreateThreadInput,
    DeleteThreadInput,
    GetThreadInput,
    ListMessagesInput,
    ListMessagesOutput,
    ListThreadsInput,
    ListThreadsOutput,
    ThreadOutput,
    UpdateThreadInput,
)


class CreateThreadUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: CreateThreadInput) -> ThreadOutput: ...


class ListThreadsUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: ListThreadsInput) -> ListThreadsOutput: ...


class GetThreadUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: GetThreadInput) -> ThreadOutput: ...


class UpdateThreadUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: UpdateThreadInput) -> ThreadOutput: ...


class DeleteThreadUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: DeleteThreadInput) -> None: ...


class ListMessagesUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: ListMessagesInput) -> ListMessagesOutput: ...

