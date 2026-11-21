import pytest
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from common.constants import AuthErrorCode, MAX_ACCESS_LOG_LIMIT
from data_agent.exceptions import AuthError, register_exception_handlers
from data_agent.routers.admin import router
from data_agent.routers.dependencies import get_token_verifier, get_user_manager
from data_agent.schemas import (
    SsoIdentity, UserInfo, ListUsersRequest, ListUsersResponse, UpdateUserRequest, UpdateUserResponse,
    UserAccessLogInfo, ListUserAccessLogsRequest, ListUserAccessLogsResponse, AdminInfo,
    ListAdminsResponse, AddAdminResponse
)

_NOW = datetime(2026, 11, 22, 10, 15, tzinfo=timezone.utc)
_HEADERS = {"Authorization": "Bearer token-1"}


def _user(user_id="user.one", **overrides):
    return {"user_id": user_id, "is_active": False, "created_at": _NOW, **overrides}


def _auth_error(status_code, code):
    return AuthError(status_code=status_code, code=code, detail="Auth error")


class TestAdminRoutes:
    @pytest.fixture
    def token_verifier(self, mocker):
        verifier = mocker.MagicMock()
        verifier.verify = mocker.MagicMock(return_value=SsoIdentity(user_id="admin.one"))
        return verifier

    @pytest.fixture
    def user_manager(self, mocker):
        manager = mocker.MagicMock()
        manager.is_admin = mocker.AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def client(self, token_verifier, user_manager):
        app = FastAPI()
        app.include_router(router)
        register_exception_handlers(app)
        app.dependency_overrides[get_token_verifier] = lambda: token_verifier
        app.dependency_overrides[get_user_manager] = lambda: user_manager
        return TestClient(app)

    def test_requires_admin(self, mocker, client, user_manager):
        requests = [
            ("GET", "/admin/users"),
            ("PATCH", "/admin/users/user.one?is_active=true"),
            ("GET", "/admin/users/user.one/access-log"),
            ("GET", "/admin/admins"),
            ("PUT", "/admin/admins/user.one"),
            ("DELETE", "/admin/admins/user.one")
        ]

        for method, path in requests:
            response = client.request(method, path)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json()["code"] == "invalid_token"

        user_manager.is_admin = mocker.AsyncMock(return_value=False)

        for method, path in requests:
            response = client.request(method, path, headers=_HEADERS)

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {"detail": "Administrator access is required", "code": "admin_required"}

        user_manager.is_admin.assert_awaited_with("admin.one")
        user_manager.list_users.assert_not_called()
        user_manager.update_user.assert_not_called()
        user_manager.add_admin.assert_not_called()
        user_manager.delete_admin.assert_not_called()

    def test_list_users(self, mocker, client, user_manager):
        user_manager.list_users = mocker.AsyncMock(return_value=ListUsersResponse(
            users=[UserInfo(**_user()), UserInfo(**_user("user.two", is_active=True))]
        ))

        response = client.get("/admin/users", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert [user["user_id"] for user in response.json()["users"]] == ["user.one", "user.two"]
        assert user_manager.list_users.await_args.kwargs["request"] == ListUsersRequest(is_active=None)

        response = client.get("/admin/users?is_active=false", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert user_manager.list_users.await_args.kwargs["request"] == ListUsersRequest(is_active=False)

        user_manager.list_users = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.get("/admin/users", headers=_HEADERS)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Runtime error"

    def test_update_user(self, mocker, client, user_manager):
        user_manager.update_user = mocker.AsyncMock(return_value=UpdateUserResponse(
            **_user(is_active=True, activated_at=_NOW, activated_by="admin.one")
        ))

        response = client.patch("/admin/users/user.one?is_active=true", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is True
        assert response.json()["activated_by"] == "admin.one"

        kwargs = user_manager.update_user.await_args.kwargs

        assert kwargs == {
            "user_id": "user.one",
            "request": UpdateUserRequest(is_active=True),
            "admin_id": "admin.one"
        }

        assert client.patch("/admin/users/user.one", headers=_HEADERS).status_code == \
               status.HTTP_422_UNPROCESSABLE_CONTENT

        user_manager.update_user = mocker.AsyncMock(
            side_effect=_auth_error(status.HTTP_404_NOT_FOUND, AuthErrorCode.USER_NOT_FOUND)
        )
        response = client.patch("/admin/users/user.two?is_active=true", headers=_HEADERS)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Auth error", "code": "user_not_found"}

        user_manager.update_user = mocker.AsyncMock(side_effect=ValueError("User id is invalid"))
        response = client.patch("/admin/users/null?is_active=true", headers=_HEADERS)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "User id is invalid"

        user_manager.update_user = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.patch("/admin/users/user.one?is_active=true", headers=_HEADERS)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_list_user_access_logs(self, mocker, client, user_manager):
        user_manager.list_user_access_logs = mocker.AsyncMock(return_value=ListUserAccessLogsResponse(
            access_logs=[UserAccessLogInfo(user_id="user.one", accessed_at=_NOW, ip_address="10.0.0.1")]
        ))

        response = client.get("/admin/users/user.one/access-log", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["access_logs"][0]["ip_address"] == "10.0.0.1"

        kwargs = user_manager.list_user_access_logs.await_args.kwargs

        assert kwargs == {"user_id": "user.one", "request": ListUserAccessLogsRequest()}

        response = client.get("/admin/users/user.one/access-log?limit=5", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert user_manager.list_user_access_logs.await_args.kwargs["request"].limit == 5

        for limit in [0, MAX_ACCESS_LOG_LIMIT + 1]:
            response = client.get(f"/admin/users/user.one/access-log?limit={limit}", headers=_HEADERS)

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        user_manager.list_user_access_logs = mocker.AsyncMock(
            side_effect=_auth_error(status.HTTP_404_NOT_FOUND, AuthErrorCode.USER_NOT_FOUND)
        )
        response = client.get("/admin/users/user.two/access-log", headers=_HEADERS)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["code"] == "user_not_found"

        user_manager.list_user_access_logs = mocker.AsyncMock(side_effect=ValueError("User id is invalid"))
        response = client.get("/admin/users/null/access-log", headers=_HEADERS)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        user_manager.list_user_access_logs = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.get("/admin/users/user.one/access-log", headers=_HEADERS)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_list_admins(self, mocker, client, user_manager):
        user_manager.list_admins = mocker.AsyncMock(return_value=ListAdminsResponse(
            admins=[AdminInfo(user_id="admin.one", added_at=_NOW, added_by="bootstrap")]
        ))

        response = client.get("/admin/admins", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "admins": [{"user_id": "admin.one", "added_at": "2026-11-22T10:15:00Z", "added_by": "bootstrap"}]
        }

        user_manager.list_admins = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.get("/admin/admins", headers=_HEADERS)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_add_admin(self, mocker, client, user_manager):
        user_manager.add_admin = mocker.AsyncMock(return_value=AddAdminResponse(
            user_id="user.one",
            added_at=_NOW,
            added_by="admin.one"
        ))

        response = client.put("/admin/admins/user.one", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["user_id"] == "user.one"
        assert response.json()["added_by"] == "admin.one"
        assert user_manager.add_admin.await_args.kwargs == {"user_id": "user.one", "admin_id": "admin.one"}

        user_manager.add_admin = mocker.AsyncMock(side_effect=ValueError("User id is invalid"))
        response = client.put("/admin/admins/null", headers=_HEADERS)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "User id is invalid"

        user_manager.add_admin = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.put("/admin/admins/user.one", headers=_HEADERS)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_delete_admin(self, mocker, client, user_manager):
        user_manager.delete_admin = mocker.AsyncMock()

        response = client.delete("/admin/admins/user.one", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert user_manager.delete_admin.await_args.kwargs == {"user_id": "user.one"}

        user_manager.delete_admin = mocker.AsyncMock(
            side_effect=_auth_error(status.HTTP_409_CONFLICT, AuthErrorCode.LAST_ADMIN)
        )
        response = client.delete("/admin/admins/admin.one", headers=_HEADERS)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json() == {"detail": "Auth error", "code": "last_admin"}

        user_manager.delete_admin = mocker.AsyncMock(
            side_effect=_auth_error(status.HTTP_404_NOT_FOUND, AuthErrorCode.ADMIN_NOT_FOUND)
        )
        response = client.delete("/admin/admins/user.two", headers=_HEADERS)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["code"] == "admin_not_found"

        user_manager.delete_admin = mocker.AsyncMock(side_effect=ValueError("User id is invalid"))
        response = client.delete("/admin/admins/null", headers=_HEADERS)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        user_manager.delete_admin = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.delete("/admin/admins/user.one", headers=_HEADERS)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
