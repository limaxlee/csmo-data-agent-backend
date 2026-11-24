from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field, AwareDatetime, computed_field

from common.constants import (
    UserStatus, MAX_USER_ID_LENGTH, MAX_SEARCH_LENGTH, DEFAULT_USER_LIMIT, MAX_USER_LIMIT,
    DEFAULT_ACCESS_LOG_LIMIT, MAX_ACCESS_LOG_LIMIT
)


class SsoIdentity(BaseModel):
    user_id: str
    email: str | None = None
    full_name: str | None = None
    department: str | None = None
    company: str | None = None
    unique_name: str | None = None
    sid: str | None = None
    roles: list[str] = []
    claims: dict[str, Any] = {}


class UserInfo(BaseModel):
    user_id: str
    is_active: bool
    is_admin: bool = False
    email: str | None = None
    full_name: str | None = None
    department: str | None = None
    company: str | None = None
    unique_name: str | None = None
    sid: str | None = None
    roles: list[str] = []
    created_at: datetime
    activated_at: datetime | None = None
    activated_by: str | None = None
    last_access_at: datetime | None = None
    last_access_ip: str | None = None

    # Worked out from the approval columns, so it is never missing, whichever statement read the account.
    @computed_field
    @property
    def status(self) -> UserStatus:
        if self.is_active:
            return UserStatus.ACTIVE

        if self.activated_at is None:
            return UserStatus.WAITING

        return UserStatus.DEACTIVATED


class GetCurrentUserResponse(BaseModel):
    user_id: str
    is_active: bool
    is_admin: bool
    email: str | None = None
    full_name: str | None = None
    department: str | None = None
    company: str | None = None
    created_at: datetime


class ListUsersRequest(BaseModel):
    search: str | None = Field(default=None, max_length=MAX_SEARCH_LENGTH)
    status: UserStatus | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
    limit: int = Field(default=DEFAULT_USER_LIMIT, ge=1, le=MAX_USER_LIMIT)
    offset: int = Field(default=0, ge=0)


class ListUsersResponse(BaseModel):
    users: list[UserInfo] = []
    total: int = 0


class UpdateUserRequest(BaseModel):
    is_active: bool


class UpdateUserResponse(UserInfo):
    pass


class UserAccessLogInfo(BaseModel):
    user_id: str
    accessed_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None


class ListUserAccessLogsRequest(BaseModel):
    limit: int = Field(default=DEFAULT_ACCESS_LOG_LIMIT, ge=1, le=MAX_ACCESS_LOG_LIMIT)


class ListUserAccessLogsResponse(BaseModel):
    access_logs: list[UserAccessLogInfo] = []


class ListAllAccessLogsRequest(BaseModel):
    user_id: str | None = Field(default=None, max_length=MAX_USER_ID_LENGTH)
    search: str | None = Field(default=None, max_length=MAX_SEARCH_LENGTH)
    accessed_from: AwareDatetime | None = None
    accessed_to: AwareDatetime | None = None
    limit: int = Field(default=DEFAULT_ACCESS_LOG_LIMIT, ge=1, le=MAX_ACCESS_LOG_LIMIT)
    offset: int = Field(default=0, ge=0)


class ListAllAccessLogsResponse(BaseModel):
    access_logs: list[UserAccessLogInfo] = []
    total: int = 0


class AdminInfo(BaseModel):
    user_id: str
    added_at: datetime
    added_by: str | None = None


class ListAdminsResponse(BaseModel):
    admins: list[AdminInfo] = []


class AddAdminResponse(AdminInfo):
    pass
