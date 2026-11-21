"""Thread controller — conversation thread and message management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.thread.infrastructure.dependencies import (
    get_create_thread_handler,
    get_delete_thread_handler,
    get_thread_handler,
    get_list_messages_handler,
    get_list_threads_handler,
    get_update_thread_handler,
)
from src.container.database.engine import get_db
from src.auth.domain.entities import User
from src.thread.presentation.dtos.thread_dto import (
    MessageListResponse,
    ThreadCreateRequest,
    ThreadListResponse,
    ThreadResponse,
    ThreadUpdateRequest,
)
from src.common.presentation.middleware.auth import get_current_user

router = APIRouter(prefix="/api/threads", tags=["Threads"])


@router.post("", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    data: ThreadCreateRequest,
    current_user: User = Depends(get_current_user),
    handler=Depends(get_create_thread_handler),
) -> ThreadResponse:
    """Create a new conversation thread."""
    from src.thread.application.dto import CreateThreadInput

    output = await handler.execute(
        CreateThreadInput(user_id=current_user.id.value, title=data.title)
    )
    return ThreadResponse.from_output(output)


@router.get("", response_model=ThreadListResponse)
async def list_threads(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    handler=Depends(get_list_threads_handler),
) -> ThreadListResponse:
    """List the current user's conversation threads."""
    from src.thread.application.dto import ListThreadsInput

    output = await handler.execute(
        ListThreadsInput(user_id=current_user.id.value, offset=offset, limit=limit)
    )
    return ThreadListResponse.from_output(output)


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    handler=Depends(get_thread_handler),
) -> ThreadResponse:
    """Get a specific thread."""
    from src.thread.application.dto import GetThreadInput

    output = await handler.execute(
        GetThreadInput(user_id=current_user.id.value, thread_id=thread_id)
    )
    return ThreadResponse.from_output(output)


@router.patch("/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: uuid.UUID,
    data: ThreadUpdateRequest,
    current_user: User = Depends(get_current_user),
    handler=Depends(get_update_thread_handler),
) -> ThreadResponse:
    """Rename a thread."""
    from src.thread.application.dto import UpdateThreadInput

    output = await handler.execute(
        UpdateThreadInput(user_id=current_user.id.value, thread_id=thread_id, title=data.title)
    )
    return ThreadResponse.from_output(output)


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_thread(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    handler=Depends(get_delete_thread_handler),
) -> None:
    """Delete a thread and all related data."""
    from src.thread.application.dto import DeleteThreadInput

    await handler.execute(
        DeleteThreadInput(user_id=current_user.id.value, thread_id=thread_id)
    )


@router.get("/{thread_id}/messages", response_model=MessageListResponse)
async def list_messages(
    thread_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    handler=Depends(get_list_messages_handler),
) -> MessageListResponse:
    """List messages in a thread (for conversation restoration)."""
    from src.thread.application.dto import ListMessagesInput

    output = await handler.execute(
        ListMessagesInput(user_id=current_user.id.value, thread_id=thread_id, offset=offset, limit=limit)
    )
    return MessageListResponse.from_output(output)
