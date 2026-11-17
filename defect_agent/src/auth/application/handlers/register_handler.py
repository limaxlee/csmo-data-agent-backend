"""Register handler — user registration."""

from __future__ import annotations

from src.auth.application.ports.out.repositories import UserRepository
from src.auth.application.ports.out.gateways import (
    PasswordEncoder,
    TokenProvider,
)
from src.auth.application.dto import AuthOutput, RegisterInput
from src.auth.application.ports.in_ import RegisterUseCase
from src.auth.domain.entities import User
from src.auth.domain.exceptions import EmailAlreadyRegistered


class RegisterHandler(RegisterUseCase):
    def __init__(
        self,
        user_repo: UserRepository,
        password_hasher: PasswordEncoder,
        token_service: TokenProvider,
    ) -> None:
        self._user_repo = user_repo
        self._hasher = password_hasher
        self._tokens = token_service

    async def execute(self, inp: RegisterInput) -> AuthOutput:
        email = inp.email.strip().lower()
        existing = self._user_repo.find_by_email(email)
        if existing:
            raise EmailAlreadyRegistered(f"Email already registered: {email}")

        user = User.create(
            email=email,
            password_hash=self._hasher.hash_password(inp.password),
            name=inp.name,
        )
        saved = self._user_repo.save(user)
        return self._make_auth_output(saved)

    def _make_auth_output(self, user: User) -> AuthOutput:
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
