"""Auth controller — local migration login and central SSO account mapping."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.auth.infrastructure.dependencies import (
    get_login_handler,
    get_refresh_token_handler,
)
from src.container.database.engine import get_db
from src.auth.application.sso_account_service import SsoAccountService
from src.auth.application.dto.sso import SsoIdentity
from src.auth.domain.exceptions import PasswordRegistrationDisabled
from src.auth.infrastructure.adapters.repositories.user_repository_adapter import UserRepositoryAdapter
from src.auth.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from src.auth.infrastructure.service_token_verifier import ServiceTokenVerifier
from src.auth.domain.entities import User
from src.auth.presentation.dtos.auth_dto import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SsoLinkRequest,
    TokenResponse,
    UserResponse,
)
from src.common.presentation.middleware.auth import (
    get_current_user,
    get_local_current_user,
    get_sso_identity,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
) -> TokenResponse:
    """Local signup is retired; accounts are provisioned through SSO."""
    raise PasswordRegistrationDisabled("Use Samsung SSO to create an account")


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    handler=Depends(get_login_handler),
) -> TokenResponse:
    """Login and receive JWT tokens."""
    output = await handler.execute(data.to_input())
    return TokenResponse.from_output(output)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshRequest,
    handler=Depends(get_refresh_token_handler),
) -> TokenResponse:
    """Refresh access token using a refresh token."""
    output = await handler.execute(data.to_input())
    return TokenResponse.from_output(output)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get current user info."""
    return _user_response(current_user)


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id.value,
        email=user.email,
        name=user.name,
        role=user.role,
        created_at=user.created_at,  # type: ignore[arg-type]
    )


@router.post("/sso/link", response_model=UserResponse)
async def link_sso(
    data: SsoLinkRequest,
    local_user: User = Depends(get_local_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Prove both logins, then attach SSO to the existing local account."""
    identity = ServiceTokenVerifier().verify(data.service_token)
    user = SsoAccountService(UserRepositoryAdapter(UserRepositoryImpl(db))).link(
        local_user, identity
    )
    return _user_response(user)


@router.post("/sso/provision", response_model=UserResponse)
async def provision_sso(
    identity: SsoIdentity = Depends(get_sso_identity),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Create a passwordless user only when no local identity conflicts."""
    user = SsoAccountService(UserRepositoryAdapter(UserRepositoryImpl(db))).provision(identity)
    return _user_response(user)
