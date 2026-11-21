"""Thread repository implementation — queries ThreadEntity directly."""

from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.run.infrastructure.entity.run_entity import RunEntity
from src.thread.domain.exceptions import ThreadDeletionConflict
from src.thread.infrastructure.entity.thread_entity import ThreadEntity, MessageEntity
from src.train_data.infrastructure.legacy_tables import InputPreparation
from src.train_data.infrastructure.native_models import NativeUpload

_ACTIVE_RUN_STATUSES = ("queued", "running", "requires_input")
_PREPARING_INPUT_STATUSES = ("waiting", "queued", "preparing", "publishing")


class ThreadRepositoryImpl:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id_and_user(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> ThreadEntity | None:
        return (
            self._db.query(ThreadEntity)
            .filter(ThreadEntity.id == thread_id, ThreadEntity.user_id == user_id)
            .first()
        )

    def find_by_agent_thread_id(self, agent_thread_id: str, user_id: uuid.UUID) -> ThreadEntity | None:
        return (
            self._db.query(ThreadEntity)
            .filter(ThreadEntity.agent_thread_id == agent_thread_id, ThreadEntity.user_id == user_id)
            .first()
        )

    def save(self, orm: ThreadEntity) -> ThreadEntity:
        # merge (not add) so that re-saving an existing thread issues an UPDATE:
        # the adapter always hands us a fresh transient entity built from the domain object.
        merged = self._db.merge(orm)
        self._db.commit()
        self._db.refresh(merged)
        return merged

    def delete(self, orm: ThreadEntity) -> None:
        # Re-fetch under row lock so concurrent upload/run reservation cannot race with deletion.
        existing = (
            self._db.query(ThreadEntity)
            .filter(ThreadEntity.id == orm.id)
            .with_for_update()
            .first()
        )
        if not existing:
            return
        if self._db.query(RunEntity.id).filter(
            RunEntity.thread_id == existing.id,
            RunEntity.status.in_(_ACTIVE_RUN_STATUSES),
        ).first():
            self._db.rollback()
            raise ThreadDeletionConflict(
                "실행 중에는 대화를 삭제할 수 없습니다.",
                code="thread_has_active_run",
            )
        from src.train_data.infrastructure.native_service import NativeInputs

        if self._db.query(InputPreparation.id).filter(
            InputPreparation.thread_id == existing.id,
            InputPreparation.status.in_(_PREPARING_INPUT_STATUSES),
        ).first() or NativeInputs(self._db, None).has_live_uploads(existing.id):
            self._db.rollback()
            raise ThreadDeletionConflict(
                "업로드 진행 중에는 대화를 삭제할 수 없습니다.",
                code="input_upload_in_progress",
            )
        self._db.delete(existing)
        self._db.commit()

    def list_by_user(
        self, user_id: uuid.UUID, offset: int = 0, limit: int = 50,
    ) -> tuple[list[tuple[ThreadEntity, int]], int]:
        query = (
            self._db.query(ThreadEntity, func.count(MessageEntity.id).label("message_count"))
            .outerjoin(MessageEntity, MessageEntity.thread_id == ThreadEntity.id)
            .filter(ThreadEntity.user_id == user_id)
            .group_by(ThreadEntity.id)
            # created_at, not updated_at: a rename must not reorder a user's thread list.
            .order_by(ThreadEntity.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        results = query.all()
        total = self._db.query(ThreadEntity).filter(ThreadEntity.user_id == user_id).count()
        return results, total

