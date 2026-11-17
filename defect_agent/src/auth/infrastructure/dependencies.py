"""Auth Context — DI providers for repository adapters and use case handlers."""

from __future__ import annotations

from fastapi import Depends

from src.auth.application.handlers import LoginHandler, RefreshTokenHandler, RegisterHandler
from src.auth.application.ports.out.gateways import PasswordEncoder, TokenProvider
from src.auth.infrastructure.adapters.repositories.user_repository_adapter import UserRepositoryAdapter
from src.auth.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from src.container.database.engine import get_db
from src.container.infrastructure import get_password_hasher, get_token_service


# ── Repository Adapter ──

def get_user_repo_adapter(db=Depends(get_db)) -> UserRepositoryAdapter:
    return UserRepositoryAdapter(UserRepositoryImpl(db))


# ── Handlers ──

def get_register_handler(
    user_repo: UserRepositoryAdapter = Depends(get_user_repo_adapter),
    hasher: PasswordEncoder = Depends(get_password_hasher),
    tokens: TokenProvider = Depends(get_token_service),
) -> RegisterHandler:
    return RegisterHandler(user_repo, hasher, tokens)


def get_login_handler(
    user_repo: UserRepositoryAdapter = Depends(get_user_repo_adapter),
    hasher: PasswordEncoder = Depends(get_password_hasher),
    tokens: TokenProvider = Depends(get_token_service),
) -> LoginHandler:
    return LoginHandler(user_repo, hasher, tokens)


def get_refresh_token_handler(
    user_repo: UserRepositoryAdapter = Depends(get_user_repo_adapter),
    tokens: TokenProvider = Depends(get_token_service),
) -> RefreshTokenHandler:
    return RefreshTokenHandler(user_repo, tokens)
