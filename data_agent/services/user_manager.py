import logging
from fastapi import status

from common.constants import AuthErrorCode
from data_agent.exceptions import AuthError
from data_agent.infra import UserRepository
from data_agent.schemas import (
    SsoIdentity, UserInfo, GetCurrentUserResponse, ListUsersRequest, ListUsersResponse,
    UpdateUserRequest, UpdateUserResponse, UserAccessLogInfo, ListUserAccessLogsRequest,
    ListUserAccessLogsResponse, AdminInfo, ListAdminsResponse, AddAdminResponse
)
from data_agent.utils import normalize_user_id

logger = logging.getLogger(__name__)


class UserManager:
    def __init__(self, user_repository: UserRepository):
        self._users = user_repository

    @staticmethod
    def _user_not_found(user_id: str) -> AuthError:
        return AuthError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=AuthErrorCode.USER_NOT_FOUND,
            detail=f"User {user_id} is not found"
        )

    async def get_current_user(
            self,
            identity: SsoIdentity,
            ip_address: str | None = None,
            user_agent: str | None = None
    ) -> GetCurrentUserResponse:
        try:
            user = await self._users.record_access(identity, ip_address, user_agent)

            # An admin always has access, whatever the approval state of the account is.
            return GetCurrentUserResponse(**{**user, "is_active": user["is_active"] or user["is_admin"]})
        except Exception as e:
            logger.exception(f"Failed to get current user {identity.user_id}: {str(e)}")
            raise

    async def authorize(
            self,
            identity: SsoIdentity,
            ip_address: str | None = None,
            user_agent: str | None = None
    ) -> UserInfo:
        try:
            user = await self._users.get_user(identity.user_id)
            if user is None:
                user = await self._users.record_access(identity, ip_address, user_agent)
        except Exception as e:
            logger.exception(f"Failed to authorize user {identity.user_id}: {str(e)}")
            raise

        if not (user["is_active"] or user["is_admin"]):
            logger.info(f"Rejected request of user {identity.user_id}: account is waiting for approval")
            raise AuthError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=AuthErrorCode.ACCOUNT_INACTIVE,
                detail="This account is waiting for approval"
            )

        return UserInfo(**user)

    async def is_admin(self, user_id: str) -> bool:
        try:
            return await self._users.is_admin(user_id)
        except Exception as e:
            logger.exception(f"Failed to check admin rights of user {user_id}: {str(e)}")
            raise

    async def list_users(self, request: ListUsersRequest) -> ListUsersResponse:
        try:
            users = await self._users.list_users(is_active=request.is_active)

            logger.info(f"Listed {len(users)} user(s)")
            return ListUsersResponse(users=[UserInfo(**user) for user in users])
        except Exception as e:
            logger.exception(f"Failed to list users: {str(e)}")
            raise

    async def update_user(self, user_id: str, request: UpdateUserRequest, admin_id: str) -> UpdateUserResponse:
        user_id = normalize_user_id(user_id)
        try:
            user = await self._users.set_user_active(
                user_id=user_id,
                is_active=request.is_active,
                admin_id=admin_id
            )
        except Exception as e:
            logger.exception(f"Failed to update user {user_id}: {str(e)}")
            raise

        if user is None:
            raise self._user_not_found(user_id)

        return UpdateUserResponse(**user)

    async def list_user_access_logs(
            self,
            user_id: str,
            request: ListUserAccessLogsRequest
    ) -> ListUserAccessLogsResponse:
        user_id = normalize_user_id(user_id)
        try:
            user = await self._users.get_user(user_id)
            access_logs = await self._users.list_access_logs(user_id, request.limit) if user else []
        except Exception as e:
            logger.exception(f"Failed to list access logs of user {user_id}: {str(e)}")
            raise

        if user is None:
            raise self._user_not_found(user_id)

        logger.info(f"Listed {len(access_logs)} access log(s) of user {user_id}")
        return ListUserAccessLogsResponse(access_logs=[UserAccessLogInfo(**item) for item in access_logs])

    async def list_admins(self) -> ListAdminsResponse:
        try:
            admins = await self._users.list_admins()

            logger.info(f"Listed {len(admins)} admin(s)")
            return ListAdminsResponse(admins=[AdminInfo(**admin) for admin in admins])
        except Exception as e:
            logger.exception(f"Failed to list admins: {str(e)}")
            raise

    async def add_admin(self, user_id: str, admin_id: str) -> AddAdminResponse:
        user_id = normalize_user_id(user_id)
        try:
            admin = await self._users.add_admin(user_id=user_id, admin_id=admin_id)
            return AddAdminResponse(**admin)
        except Exception as e:
            logger.exception(f"Failed to add user {user_id} to admins: {str(e)}")
            raise

    async def delete_admin(self, user_id: str) -> None:
        user_id = normalize_user_id(user_id)
        try:
            is_admin = await self._users.is_admin(user_id)
            deleted = await self._users.delete_admin(user_id) if is_admin else False
        except Exception as e:
            logger.exception(f"Failed to remove user {user_id} from admins: {str(e)}")
            raise

        if not is_admin:
            raise AuthError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=AuthErrorCode.ADMIN_NOT_FOUND,
                detail=f"User {user_id} is not an admin"
            )

        if not deleted:
            raise AuthError(
                status_code=status.HTTP_409_CONFLICT,
                code=AuthErrorCode.LAST_ADMIN,
                detail="The last admin cannot be removed"
            )
