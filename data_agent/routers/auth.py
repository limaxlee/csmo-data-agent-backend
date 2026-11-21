import logging
from fastapi import APIRouter, status, HTTPException, Request

from data_agent.routers.dependencies import IdentityDep, UserManagerDep, get_client_ip, get_user_agent
from data_agent.schemas import GetCurrentUserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/me",
    response_model=GetCurrentUserResponse,
    status_code=status.HTTP_200_OK
)
async def get_current_user(
        request: Request,
        identity: IdentityDep,
        user_manager: UserManagerDep
):
    try:
        return await user_manager.get_current_user(
            identity=identity,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
