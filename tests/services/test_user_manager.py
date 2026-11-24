import pytest
from datetime import datetime, timezone
from starlette import status

from common.constants import AuthErrorCode, UserStatus
from data_agent.exceptions import AuthError
from data_agent.schemas import (
    SsoIdentity, ListUsersRequest, UpdateUserRequest, ListUserAccessLogsRequest, ListAllAccessLogsRequest
)
from data_agent.services.user_manager import UserManager

_NOW = datetime(2026, 11, 22, 10, 15, tzinfo=timezone.utc)


def _identity(user_id="user.one"):
    return SsoIdentity(user_id=user_id, email=f"{user_id}@samsung.com")


def _user(**overrides):
    user = {
        "user_id": "user.one",
        "is_active": False,
        "is_admin": False,
        "email": "user.one@samsung.com",
        "full_name": "user.one@samsung.com",
        "department": "Test Dept",
        "company": "Test Co",
        "unique_name": "CORP\\user.one",
        "sid": "S-1-5-21-1",
        "roles": ["group-a"],
        "sso_claims": {"sub": "user.one"},
        "created_at": _NOW,
        "activated_at": None,
        "activated_by": None,
        "last_access_at": _NOW,
        "last_access_ip": "10.0.0.1",
        "sso_updated_at": _NOW
    }
    user.update(overrides)
    return user


class TestUserManager:
    @pytest.fixture
    def user_repository(self, mocker):
        repository = mocker.MagicMock()
        repository.record_access = mocker.AsyncMock(return_value=_user())
        repository.get_user = mocker.AsyncMock(return_value=_user())
        repository.list_users = mocker.AsyncMock(return_value=[])
        repository.count_users = mocker.AsyncMock(return_value=0)
        repository.set_user_active = mocker.AsyncMock(return_value=_user(is_active=True))
        repository.list_access_logs = mocker.AsyncMock(return_value=[])
        repository.list_all_access_logs = mocker.AsyncMock(return_value=[])
        repository.count_all_access_logs = mocker.AsyncMock(return_value=0)
        repository.is_admin = mocker.AsyncMock(return_value=False)
        repository.list_admins = mocker.AsyncMock(return_value=[])
        repository.add_admin = mocker.AsyncMock()
        repository.delete_admin = mocker.AsyncMock(return_value=True)
        return repository

    @pytest.fixture
    def user_manager(self, user_repository):
        return UserManager(user_repository=user_repository)

    @pytest.mark.asyncio
    async def test_get_current_user(self, mocker, user_repository, user_manager):
        response = await user_manager.get_current_user(_identity(), "10.0.0.1", "pytest")

        assert response.model_dump() == {
            "user_id": "user.one",
            "is_active": False,
            "is_admin": False,
            "email": "user.one@samsung.com",
            "full_name": "user.one@samsung.com",
            "department": "Test Dept",
            "company": "Test Co",
            "created_at": _NOW
        }
        user_repository.record_access.assert_awaited_once_with(_identity(), "10.0.0.1", "pytest")

        user_repository.record_access = mocker.AsyncMock(return_value=_user(is_active=True))
        response = await user_manager.get_current_user(_identity())

        assert response.is_active is True
        assert response.is_admin is False

        # An admin is reported as active even while the account itself is not approved.
        user_repository.record_access = mocker.AsyncMock(return_value=_user(is_admin=True))
        response = await user_manager.get_current_user(_identity())

        assert response.is_active is True
        assert response.is_admin is True

        user_repository.record_access = mocker.AsyncMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            await user_manager.get_current_user(_identity())

    @pytest.mark.asyncio
    async def test_authorize(self, mocker, user_repository, user_manager):
        user_repository.get_user = mocker.AsyncMock(return_value=_user(is_active=True))

        user = await user_manager.authorize(_identity(), "10.0.0.1", "pytest")

        assert user.user_id == "user.one"
        assert user.is_active is True
        user_repository.get_user.assert_awaited_once_with("user.one")
        user_repository.record_access.assert_not_awaited()

        user_repository.get_user = mocker.AsyncMock(return_value=_user(is_admin=True))
        user = await user_manager.authorize(_identity())

        assert user.is_active is False
        assert user.is_admin is True

    @pytest.mark.asyncio
    async def test_authorize_rejects_inactive_user(self, mocker, user_repository, user_manager):
        with pytest.raises(AuthError) as error:
            await user_manager.authorize(_identity())

        assert error.value.status_code == status.HTTP_403_FORBIDDEN
        assert error.value.code == AuthErrorCode.ACCOUNT_INACTIVE
        user_repository.record_access.assert_not_awaited()

        # The first request of a new person creates the account, which then waits for approval.
        user_repository.get_user = mocker.AsyncMock(return_value=None)

        with pytest.raises(AuthError) as error:
            await user_manager.authorize(_identity(), "10.0.0.1", "pytest")

        assert error.value.code == AuthErrorCode.ACCOUNT_INACTIVE
        user_repository.record_access.assert_awaited_once_with(_identity(), "10.0.0.1", "pytest")

        user_repository.get_user = mocker.AsyncMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            await user_manager.authorize(_identity())

    @pytest.mark.asyncio
    async def test_is_admin(self, mocker, user_repository, user_manager):
        assert await user_manager.is_admin("user.one") is False
        user_repository.is_admin.assert_awaited_once_with("user.one")

        user_repository.is_admin = mocker.AsyncMock(return_value=True)
        assert await user_manager.is_admin("user.one") is True

        user_repository.is_admin = mocker.AsyncMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            await user_manager.is_admin("user.one")

    @pytest.mark.asyncio
    async def test_list_users(self, mocker, user_repository, user_manager):
        user_repository.list_users = mocker.AsyncMock(return_value=[
            _user(),
            _user(user_id="user.two", is_active=True, activated_at=_NOW),
            _user(user_id="user.three", activated_at=_NOW)
        ])
        user_repository.count_users = mocker.AsyncMock(return_value=12)

        response = await user_manager.list_users(ListUsersRequest(is_active=False))

        assert [user.user_id for user in response.users] == ["user.one", "user.two", "user.three"]
        assert [user.status for user in response.users] == [
            UserStatus.WAITING, UserStatus.ACTIVE, UserStatus.DEACTIVATED
        ]
        assert response.total == 12
        assert response.users[0].last_access_ip == "10.0.0.1"
        assert "sso_claims" not in response.users[0].model_dump()

        filters = {"search": None, "status": None, "is_active": False, "is_admin": None}

        user_repository.list_users.assert_awaited_once_with(**filters, limit=50, offset=0)
        user_repository.count_users.assert_awaited_once_with(**filters)

        user_repository.list_users = mocker.AsyncMock(return_value=[])
        user_repository.count_users = mocker.AsyncMock(return_value=0)

        response = await user_manager.list_users(ListUsersRequest(
            search="  Hong  ",
            status=UserStatus.WAITING,
            is_admin=False,
            limit=10,
            offset=20
        ))

        assert response.users == []
        assert response.total == 0

        filters = {"search": "Hong", "status": UserStatus.WAITING, "is_active": None, "is_admin": False}

        user_repository.list_users.assert_awaited_once_with(**filters, limit=10, offset=20)
        user_repository.count_users.assert_awaited_once_with(**filters)

        # A search box that holds only spaces filters nothing.
        await user_manager.list_users(ListUsersRequest(search="   "))

        assert user_repository.list_users.await_args.kwargs["search"] is None
        assert user_repository.count_users.await_args.kwargs["search"] is None

        user_repository.list_users = mocker.AsyncMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            await user_manager.list_users(ListUsersRequest())

        user_repository.list_users = mocker.AsyncMock(return_value=[])
        user_repository.count_users = mocker.AsyncMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            await user_manager.list_users(ListUsersRequest())

    @pytest.mark.asyncio
    async def test_update_user(self, mocker, user_repository, user_manager):
        response = await user_manager.update_user(" User.One ", UpdateUserRequest(is_active=True), "admin.one")

        assert response.user_id == "user.one"
        assert response.is_active is True
        user_repository.set_user_active.assert_awaited_once_with(
            user_id="user.one",
            is_active=True,
            admin_id="admin.one"
        )

        user_repository.set_user_active = mocker.AsyncMock(return_value=None)

        with pytest.raises(AuthError) as error:
            await user_manager.update_user("user.two", UpdateUserRequest(is_active=True), "admin.one")

        assert error.value.status_code == status.HTTP_404_NOT_FOUND
        assert error.value.code == AuthErrorCode.USER_NOT_FOUND

        with pytest.raises(ValueError, match="User id is invalid"):
            await user_manager.update_user("team/user", UpdateUserRequest(is_active=True), "admin.one")

        user_repository.set_user_active = mocker.AsyncMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            await user_manager.update_user("user.one", UpdateUserRequest(is_active=True), "admin.one")

    @pytest.mark.asyncio
    async def test_list_user_access_logs(self, mocker, user_repository, user_manager):
        user_repository.list_access_logs = mocker.AsyncMock(return_value=[
            {"user_id": "user.one", "accessed_at": _NOW, "ip_address": "10.0.0.1", "user_agent": "pytest"}
        ])

        response = await user_manager.list_user_access_logs("User.One", ListUserAccessLogsRequest(limit=5))

        assert len(response.access_logs) == 1
        assert response.access_logs[0].ip_address == "10.0.0.1"
        user_repository.list_access_logs.assert_awaited_once_with("user.one", 5)

        user_repository.get_user = mocker.AsyncMock(return_value=None)
        user_repository.list_access_logs = mocker.AsyncMock()

        with pytest.raises(AuthError) as error:
            await user_manager.list_user_access_logs("user.two", ListUserAccessLogsRequest())

        assert error.value.status_code == status.HTTP_404_NOT_FOUND
        assert error.value.code == AuthErrorCode.USER_NOT_FOUND
        user_repository.list_access_logs.assert_not_awaited()

        with pytest.raises(ValueError, match="User id is invalid"):
            await user_manager.list_user_access_logs("  ", ListUserAccessLogsRequest())

    @pytest.mark.asyncio
    async def test_list_all_access_logs(self, mocker, user_repository, user_manager):
        user_repository.list_all_access_logs = mocker.AsyncMock(return_value=[
            {"user_id": "user.one", "accessed_at": _NOW, "ip_address": "10.0.0.1", "user_agent": "pytest"},
            {"user_id": "user.two", "accessed_at": _NOW, "ip_address": "10.0.0.2", "user_agent": None}
        ])
        user_repository.count_all_access_logs = mocker.AsyncMock(return_value=40)

        response = await user_manager.list_all_access_logs(ListAllAccessLogsRequest())

        assert [item.user_id for item in response.access_logs] == ["user.one", "user.two"]
        assert response.access_logs[0].ip_address == "10.0.0.1"
        assert response.total == 40

        filters = {"user_id": None, "search": None, "accessed_from": None, "accessed_to": None}

        user_repository.list_all_access_logs.assert_awaited_once_with(**filters, limit=100, offset=0)
        user_repository.count_all_access_logs.assert_awaited_once_with(**filters)

        user_repository.list_all_access_logs = mocker.AsyncMock(return_value=[])
        user_repository.count_all_access_logs = mocker.AsyncMock(return_value=0)

        response = await user_manager.list_all_access_logs(ListAllAccessLogsRequest(
            user_id=" User.One ",
            search=" 10.0 ",
            accessed_from=_NOW,
            accessed_to=_NOW,
            limit=10,
            offset=20
        ))

        assert response.access_logs == []
        assert response.total == 0

        filters = {"user_id": "User.One", "search": "10.0", "accessed_from": _NOW, "accessed_to": _NOW}

        user_repository.list_all_access_logs.assert_awaited_once_with(**filters, limit=10, offset=20)
        user_repository.count_all_access_logs.assert_awaited_once_with(**filters)

        # An empty filter is no filter: it must not be searched for as an empty login ID.
        await user_manager.list_all_access_logs(ListAllAccessLogsRequest(user_id="", search="   "))

        assert user_repository.list_all_access_logs.await_args.kwargs["user_id"] is None
        assert user_repository.list_all_access_logs.await_args.kwargs["search"] is None

        user_repository.list_all_access_logs = mocker.AsyncMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            await user_manager.list_all_access_logs(ListAllAccessLogsRequest())

    @pytest.mark.asyncio
    async def test_list_admins(self, mocker, user_repository, user_manager):
        user_repository.list_admins = mocker.AsyncMock(return_value=[
            {"user_id": "admin.one", "added_at": _NOW, "added_by": "bootstrap"}
        ])

        response = await user_manager.list_admins()

        assert [admin.user_id for admin in response.admins] == ["admin.one"]
        assert response.admins[0].added_by == "bootstrap"

        user_repository.list_admins = mocker.AsyncMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            await user_manager.list_admins()

    @pytest.mark.asyncio
    async def test_add_admin(self, mocker, user_repository, user_manager):
        user_repository.add_admin = mocker.AsyncMock(
            return_value={"user_id": "user.one", "added_at": _NOW, "added_by": "admin.one"}
        )

        response = await user_manager.add_admin(" User.One ", "admin.one")

        assert response.user_id == "user.one"
        assert response.added_by == "admin.one"
        user_repository.add_admin.assert_awaited_once_with(user_id="user.one", admin_id="admin.one")

        with pytest.raises(ValueError, match="User id is invalid"):
            await user_manager.add_admin("null", "admin.one")

        user_repository.add_admin = mocker.AsyncMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            await user_manager.add_admin("user.one", "admin.one")

    @pytest.mark.asyncio
    async def test_delete_admin(self, mocker, user_repository, user_manager):
        user_repository.is_admin = mocker.AsyncMock(return_value=True)

        await user_manager.delete_admin(" User.One ")

        user_repository.is_admin.assert_awaited_once_with("user.one")
        user_repository.delete_admin.assert_awaited_once_with("user.one")

        # Nothing was deleted although the user is an admin: it is the last one.
        user_repository.delete_admin = mocker.AsyncMock(return_value=False)

        with pytest.raises(AuthError) as error:
            await user_manager.delete_admin("user.one")

        assert error.value.status_code == status.HTTP_409_CONFLICT
        assert error.value.code == AuthErrorCode.LAST_ADMIN

        user_repository.is_admin = mocker.AsyncMock(return_value=False)
        user_repository.delete_admin = mocker.AsyncMock()

        with pytest.raises(AuthError) as error:
            await user_manager.delete_admin("user.two")

        assert error.value.status_code == status.HTTP_404_NOT_FOUND
        assert error.value.code == AuthErrorCode.ADMIN_NOT_FOUND
        user_repository.delete_admin.assert_not_awaited()

        with pytest.raises(ValueError, match="User id is invalid"):
            await user_manager.delete_admin("team/user")

        user_repository.is_admin = mocker.AsyncMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            await user_manager.delete_admin("user.one")
