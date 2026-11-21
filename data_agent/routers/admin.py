import logging
from typing import Annotated
from fastapi import APIRouter, status, HTTPException, Path, Depends

from data_agent.exceptions import AuthError
from data_agent.routers.dependencies import AdminDep, UserManagerDep, require_admin
from data_agent.schemas import (
    ListUsersRequest, ListUsersResponse, UpdateUserRequest, UpdateUserResponse,
    ListUserAccessLogsRequest, ListUserAccessLogsResponse, ListAdminsResponse, AddAdminResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get(
    "/users",
    response_model=ListUsersResponse,
    status_code=status.HTTP_200_OK
)
async def list_users(
        request: Annotated[ListUsersRequest, Depends()],
        user_manager: UserManagerDep
):
    try:
        return await user_manager.list_users(request=request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch(
    "/users/{user_id}",
    response_model=UpdateUserResponse,
    status_code=status.HTTP_200_OK
)
async def update_user(
        user_id: Annotated[str, Path()],
        request: Annotated[UpdateUserRequest, Depends()],
        admin: AdminDep,
        user_manager: UserManagerDep
):
    try:
        return await user_manager.update_user(user_id=user_id, request=request, admin_id=admin.user_id)
    except AuthError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/users/{user_id}/access-log",
    response_model=ListUserAccessLogsResponse,
    status_code=status.HTTP_200_OK
)
async def list_user_access_logs(
        user_id: Annotated[str, Path()],
        request: Annotated[ListUserAccessLogsRequest, Depends()],
        user_manager: UserManagerDep
):
    try:
        return await user_manager.list_user_access_logs(user_id=user_id, request=request)
    except AuthError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/admins",
    response_model=ListAdminsResponse,
    status_code=status.HTTP_200_OK
)
async def list_admins(user_manager: UserManagerDep):
    try:
        return await user_manager.list_admins()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put(
    "/admins/{user_id}",
    response_model=AddAdminResponse,
    status_code=status.HTTP_200_OK
)
async def add_admin(
        user_id: Annotated[str, Path()],
        admin: AdminDep,
        user_manager: UserManagerDep
):
    try:
        return await user_manager.add_admin(user_id=user_id, admin_id=admin.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/admins/{user_id}",
    status_code=status.HTTP_200_OK
)
async def delete_admin(
        user_id: Annotated[str, Path()],
        user_manager: UserManagerDep
):
    try:
        await user_manager.delete_admin(user_id=user_id)
    except AuthError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
