"""Plan repository implementation — queries PlanEntity directly."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.plan.infrastructure.entity.plan_entity import PlanEntity


class PlanRepositoryImpl:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_thread_and_plan_id(self, thread_id: uuid.UUID, plan_id: str) -> PlanEntity | None:
        return (
            self._db.query(PlanEntity)
            .filter(PlanEntity.thread_id == thread_id, PlanEntity.plan_id == plan_id)
            .first()
        )

    def save(self, orm: PlanEntity) -> PlanEntity:
        """Persist a plan, keyed by (thread_id, plan_id) rather than by ``id``.

        The caller looks for an existing row and then inserts if it found none,
        which is not atomic: two runs on the same thread can both be told about
        plan "0" and both decide to insert. uq_plans_thread_plan rejects the
        second, and the right answer there is not to fail the event — by that
        table's own definition the two rows are the same plan — so the content
        goes onto whichever row won.
        """
        natural_key = (orm.thread_id, orm.plan_id)
        content, status = orm.content, orm.status

        merged = self._db.merge(orm)
        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            existing = self.find_by_thread_and_plan_id(*natural_key)
            if existing is None:
                # Not the collision we expected — a thread that has since been
                # deleted, say. Swallowing it would drop the plan silently.
                raise
            existing.content = content
            existing.status = status
            self._db.commit()
            self._db.refresh(existing)
            return existing
        self._db.refresh(merged)
        return merged

    def list_by_thread(self, thread_id: uuid.UUID) -> list[PlanEntity]:
        return (
            self._db.query(PlanEntity)
            .filter(PlanEntity.thread_id == thread_id)
            .order_by(PlanEntity.created_at.asc())
            .all()
        )

