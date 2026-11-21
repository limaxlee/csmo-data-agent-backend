from typing import Annotated
from fastapi import status, Path, Depends, Header, Request

from common.constants import AuthErrorCode, BEARER_PREFIX, MAX_USER_AGENT_LENGTH
from data_agent.exceptions import AuthError
from data_agent.schemas import SsoIdentity, UserInfo
from data_agent.services import TokenVerifier, UserManager


def get_token_verifier(request: Request) -> TokenVerifier:
    return request.app.state.token_verifier


def get_user_manager(request: Request) -> UserManager:
    return request.app.state.user_manager


TokenVerifierDep = Annotated[TokenVerifier, Depends(get_token_verifier)]
UserManagerDep = Annotated[UserManager, Depends(get_user_manager)]


def get_client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    user_agent = request.headers.get("user-agent")
    return user_agent[:MAX_USER_AGENT_LENGTH] if user_agent else None


def get_identity(
        token_verifier: TokenVerifierDep,
        authorization: Annotated[str | None, Header()] = None
) -> SsoIdentity:
    token = ""
    if authorization and authorization.startswith(BEARER_PREFIX):
        token = authorization.removeprefix(BEARER_PREFIX).strip()

    if not token:
        raise AuthError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=AuthErrorCode.INVALID_TOKEN,
            detail="Missing or invalid Authorization header"
        )

    return token_verifier.verify(token)


IdentityDep = Annotated[SsoIdentity, Depends(get_identity)]


async def require_active_user(
        request: Request,
        identity: IdentityDep,
        user_manager: UserManagerDep
) -> UserInfo:
    return await user_manager.authorize(
        identity=identity,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )


ActiveUserDep = Annotated[UserInfo, Depends(require_active_user)]


async def require_session_owner(
        user_id: Annotated[str, Path()],
        user: ActiveUserDep
) -> None:
    if user_id != user.user_id:
        raise AuthError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=AuthErrorCode.USER_MISMATCH,
            detail="This address belongs to another user"
        )


async def require_admin(
        identity: IdentityDep,
        user_manager: UserManagerDep
) -> SsoIdentity:
    if not await user_manager.is_admin(identity.user_id):
        raise AuthError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=AuthErrorCode.ADMIN_REQUIRED,
            detail="Administrator access is required"
        )

    return identity


AdminDep = Annotated[SsoIdentity, Depends(require_admin)]
