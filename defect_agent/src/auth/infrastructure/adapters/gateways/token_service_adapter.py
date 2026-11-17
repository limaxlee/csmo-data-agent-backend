"""Adapter: implements TokenProvider using python-jose JWT."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from src.auth.application.ports.out.gateways import TokenProvider
from src.container.settings import get_settings


class TokenServiceAdapter(TokenProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self._secret = settings.secret_key
        self._algo = settings.algorithm
        self._access_exp = settings.access_token_expire_minutes
        self._refresh_exp = settings.refresh_token_expire_minutes

    def create_access_token(self, subject: uuid.UUID, extra_claims: dict[str, Any] | None = None) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=self._access_exp)
        claims: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": "access"}
        if extra_claims:
            claims.update(extra_claims)
        return jwt.encode(claims, self._secret, algorithm=self._algo)

    def create_refresh_token(self, subject: uuid.UUID) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=self._refresh_exp)
        claims = {"sub": str(subject), "exp": expire, "type": "refresh"}
        return jwt.encode(claims, self._secret, algorithm=self._algo)

    def decode_token(self, token: str) -> dict[str, Any]:
        return jwt.decode(token, self._secret, algorithms=[self._algo])