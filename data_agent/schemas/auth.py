from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field

from common.constants import DEFAULT_ACCESS_LOG_LIMIT, MAX_ACCESS_LOG_LIMIT


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
    is_active: bool | None = None


class ListUsersResponse(BaseModel):
    users: list[UserInfo] = []


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


class AdminInfo(BaseModel):
    user_id: str
    added_at: datetime
    added_by: str | None = None


class ListAdminsResponse(BaseModel):
    admins: list[AdminInfo] = []


class AddAdminResponse(AdminInfo):
    pass
