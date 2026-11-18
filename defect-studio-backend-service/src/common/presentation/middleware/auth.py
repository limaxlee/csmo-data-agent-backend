"""Resolve local and central SSO bearer tokens to the same local User."""

from __future__ import annotations

import uuid

from fastapi import Depends, Header
from jose import JWTError
from sqlalchemy.orm import Session

from src.auth.application.dto.sso import SsoIdentity
from src.auth.application.ports.out.gateways import TokenProvider
from src.auth.domain.entities import User
from src.auth.domain.exceptions import InvalidToken, SsoAccountUnlinked
from src.auth.infrastructure.adapters.repositories.user_repository_adapter import UserRepositoryAdapter
from src.auth.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from src.auth.infrastructure.service_token_verifier import ServiceTokenVerifier
from src.container.database.engine import get_db
from src.container.infrastructure import get_token_service


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise InvalidToken("Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise InvalidToken("Missing or invalid Authorization header")
    return token


def _local_user(
    token: str, db: Session, token_service: TokenProvider, payload: dict | None = None
) -> User:
    if payload is None:
        try:
            payload = token_service.decode_token(token)
        except JWTError as exc:
            raise InvalidToken("Invalid access token") from exc
    if payload.get("type") != "access":
        raise InvalidToken("Not an access token")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise InvalidToken("Invalid token subject") from exc
    user = UserRepositoryAdapter(UserRepositoryImpl(db)).find_by_id(user_id)
    if user is None:
        raise InvalidToken("Account no longer exists")
    return user


def get_local_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
    token_service: TokenProvider = Depends(get_token_service),
) -> User:
    """Require a local access JWT; used only during account linking."""
    return _local_user(_bearer(authorization), db, token_service)


def get_sso_identity(authorization: str | None = Header(None)) -> SsoIdentity:
    """Require a verified central service JWT."""
    return ServiceTokenVerifier().verify(_bearer(authorization))


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
    token_service: TokenProvider = Depends(get_token_service),
) -> User:
    """Accept either local access JWT or a linked central service JWT."""
    token = _bearer(authorization)
    try:
        payload = token_service.decode_token(token)
    except JWTError:
        identity = ServiceTokenVerifier().verify(token)
        user = UserRepositoryAdapter(UserRepositoryImpl(db)).find_by_sso_loginid(identity.loginid)
        if user is None:
            raise SsoAccountUnlinked("SSO account is not linked")
        return user

    if payload.get("type") != "access":
        raise InvalidToken("Not an access token")
    return _local_user(token, db, token_service, payload)
