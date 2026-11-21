"""Message repository implementation — queries MessageEntity directly."""

from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.thread.infrastructure.entity.thread_entity import MessageEntity


class MessageRepositoryImpl:
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, orm: MessageEntity) -> MessageEntity:
        self._db.add(orm)
        self._db.commit()
        self._db.refresh(orm)
        return orm

    def list_by_thread(
        self, thread_id: uuid.UUID, offset: int = 0, limit: int = 100,
    ) -> tuple[list[MessageEntity], int]:
        query = (
            self._db.query(MessageEntity)
            .filter(MessageEntity.thread_id == thread_id)
            .order_by(MessageEntity.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        messages = query.all()
        total = (
            self._db.query(func.count(MessageEntity.id))
            .filter(MessageEntity.thread_id == thread_id)
            .scalar() or 0
        )
        return messages, total
