"""Refresh token handler — token refresh."""

from __future__ import annotations

import uuid

from jose import JWTError

from src.auth.application.ports.out.repositories import UserRepository
from src.auth.application.ports.out.gateways import TokenProvider
from src.auth.application.dto import AuthOutput, RefreshTokenInput
from src.auth.application.ports.in_ import RefreshTokenUseCase
from src.auth.domain.exceptions import InvalidToken


class RefreshTokenHandler(RefreshTokenUseCase):
    def __init__(
        self,
        user_repo: UserRepository,
        token_service: TokenProvider,
    ) -> None:
        self._user_repo = user_repo
        self._tokens = token_service

    async def execute(self, inp: RefreshTokenInput) -> AuthOutput:
        try:
            payload = self._tokens.decode_token(inp.refresh_token)
            if payload.get("type") != "refresh":
                raise InvalidToken("Invalid refresh token")
            user_id = uuid.UUID(payload["sub"])
        except (InvalidToken, JWTError, ValueError, KeyError):
            raise InvalidToken("Invalid refresh token")

        user = self._user_repo.find_by_id(user_id)
        if not user:
            raise InvalidToken("Account no longer exists")

        access = self._tokens.create_access_token(user.id.value, {"email": user.email, "role": user.role})
        refresh = self._tokens.create_refresh_token(user.id.value)
        return AuthOutput(
            access_token=access,
            refresh_token=refresh,
            user_id=user.id.value,
            user_email=user.email,
            user_name=user.name,
            user_role=user.role,
            user_created_at=user.created_at,
        )
