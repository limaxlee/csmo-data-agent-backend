"""User repository implementation — queries UserEntity directly."""

from __future__ import annotations

import uuid

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from src.auth.infrastructure.entity.user_entity import SsoLinkAuditEntity, UserEntity


class UserRepositoryImpl:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, user_id: uuid.UUID) -> UserEntity | None:
        return self._db.query(UserEntity).filter(UserEntity.id == user_id).first()

    def find_by_email(self, email: str) -> UserEntity | None:
        return self._db.query(UserEntity).filter(
            func.lower(UserEntity.email) == email.strip().lower()
        ).first()

    def find_by_sso_loginid(self, loginid: str) -> UserEntity | None:
        return (
            self._db.query(UserEntity)
            .filter(UserEntity.sso_loginid == loginid)
            .first()
        )

    def link_sso_loginid(self, user_id: uuid.UUID, loginid: str) -> UserEntity | None:
        result = self._db.execute(
            update(UserEntity)
            .where(UserEntity.id == user_id, UserEntity.sso_loginid.is_(None))
            .values(sso_loginid=loginid)
        )
        if result.rowcount == 1:
            self._db.add(SsoLinkAuditEntity(
                user_id=user_id, sso_loginid=loginid,
                actor_type="self", actor=str(user_id),
            ))
            self._db.commit()
        else:
            self._db.rollback()
        return self.find_by_id(user_id)

    def provision_sso_user(self, orm: UserEntity) -> UserEntity:
        self._db.add(orm)
        # Insert the user first; sso_link_audit.user_id references users.id.
        self._db.flush()
        self._db.add(SsoLinkAuditEntity(
            user_id=orm.id, sso_loginid=orm.sso_loginid,
            actor_type="provision", actor=orm.sso_loginid,
        ))
        self._db.commit()
        self._db.refresh(orm)
        return orm

    def rollback(self) -> None:
        self._db.rollback()

    def save(self, orm: UserEntity) -> UserEntity:
        self._db.add(orm)
        self._db.commit()
        self._db.refresh(orm)
        return orm
