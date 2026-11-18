"""Login handler — user authentication."""

from __future__ import annotations

from src.auth.application.ports.out.repositories import UserRepository
from src.auth.application.ports.out.gateways import (
    PasswordEncoder,
    TokenProvider,
)
from src.auth.application.dto import AuthOutput, LoginInput
from src.auth.application.ports.in_ import LoginUseCase
from src.auth.domain.exceptions import InvalidCredentials


class LoginHandler(LoginUseCase):
    def __init__(
        self,
        user_repo: UserRepository,
        password_hasher: PasswordEncoder,
        token_service: TokenProvider,
    ) -> None:
        self._user_repo = user_repo
        self._hasher = password_hasher
        self._tokens = token_service

    async def execute(self, inp: LoginInput) -> AuthOutput:
        user = self._user_repo.find_by_email(inp.email)
        if (
            not user
            or not user.password_hash
            or not self._hasher.verify_password(inp.password, user.password_hash)
        ):
            raise InvalidCredentials("Invalid email or password")
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