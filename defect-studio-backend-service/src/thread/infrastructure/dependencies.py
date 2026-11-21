"""Thread Context — DI providers for use case handlers.

ThreadRepository and MessageRepository adapters are provided by the
shared composition root (`container.infrastructure`) because they are
shared across multiple contexts.
"""

from __future__ import annotations

from fastapi import Depends

from src.thread.application.handlers import (
    CreateThreadHandler,
    DeleteThreadHandler,
    GetThreadHandler,
    ListMessagesHandler,
    ListThreadsHandler,
    UpdateThreadHandler,
)
from src.common.application.ports.out.gateways import StorageGateway
from src.thread.infrastructure.adapters.repositories.message_repository_adapter import MessageRepositoryAdapter
from src.thread.infrastructure.adapters.repositories.thread_repository_adapter import ThreadRepositoryAdapter
from src.container.infrastructure import get_message_repo_adapter, get_storage, get_thread_repo_adapter


# ── Handlers ──

def get_create_thread_handler(
    thread_repo: ThreadRepositoryAdapter = Depends(get_thread_repo_adapter),
) -> CreateThreadHandler:
    return CreateThreadHandler(thread_repo)


def get_list_threads_handler(
    thread_repo: ThreadRepositoryAdapter = Depends(get_thread_repo_adapter),
) -> ListThreadsHandler:
    return ListThreadsHandler(thread_repo)


def get_thread_handler(
    thread_repo: ThreadRepositoryAdapter = Depends(get_thread_repo_adapter),
) -> GetThreadHandler:
    return GetThreadHandler(thread_repo)


def get_update_thread_handler(
    thread_repo: ThreadRepositoryAdapter = Depends(get_thread_repo_adapter),
) -> UpdateThreadHandler:
    return UpdateThreadHandler(thread_repo)


def get_delete_thread_handler(
    thread_repo: ThreadRepositoryAdapter = Depends(get_thread_repo_adapter),
    storage: StorageGateway | None = Depends(get_storage),
) -> DeleteThreadHandler:
    resolved_storage = (
        storage
        if isinstance(storage, StorageGateway) or hasattr(storage, "list_keys")
        else None
    )
    return DeleteThreadHandler(thread_repo, storage=resolved_storage)


def get_list_messages_handler(
    thread_repo: ThreadRepositoryAdapter = Depends(get_thread_repo_adapter),
    message_repo: MessageRepositoryAdapter = Depends(get_message_repo_adapter),
) -> ListMessagesHandler:
    return ListMessagesHandler(thread_repo, message_repo)

