import pytest
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from common.constants import AuthErrorCode
from data_agent.exceptions import AuthError, register_exception_handlers
from data_agent.routers.auth import router
from data_agent.routers.dependencies import get_token_verifier, get_user_manager
from data_agent.schemas import SsoIdentity, GetCurrentUserResponse

_HEADERS = {"Authorization": "Bearer token-1", "User-Agent": "pytest"}


def _current_user(**overrides):
    user = {
        "user_id": "user.one",
        "is_active": False,
        "is_admin": False,
        "email": "user.one@samsung.com",
        "full_name": "user.one@samsung.com",
        "department": "Test Dept",
        "company": "Test Co",
        "created_at": datetime(2026, 11, 22, 10, 15, tzinfo=timezone.utc)
    }
    user.update(overrides)
    return GetCurrentUserResponse(**user)


class TestAuthRoutes:
    @pytest.fixture
    def token_verifier(self, mocker):
        verifier = mocker.MagicMock()
        verifier.verify = mocker.MagicMock(return_value=SsoIdentity(user_id="user.one"))
        return verifier

    @pytest.fixture
    def user_manager(self, mocker):
        manager = mocker.MagicMock()
        manager.get_current_user = mocker.AsyncMock(return_value=_current_user())
        return manager

    @pytest.fixture
    def client(self, token_verifier, user_manager):
        app = FastAPI()
        app.include_router(router)
        register_exception_handlers(app)
        app.dependency_overrides[get_token_verifier] = lambda: token_verifier
        app.dependency_overrides[get_user_manager] = lambda: user_manager
        return TestClient(app)

    def test_get_current_user(self, mocker, client, user_manager):
        response = client.get("/auth/me", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "user_id": "user.one",
            "is_active": False,
            "is_admin": False,
            "email": "user.one@samsung.com",
            "full_name": "user.one@samsung.com",
            "department": "Test Dept",
            "company": "Test Co",
            "created_at": "2026-11-22T10:15:00Z"
        }

        kwargs = user_manager.get_current_user.await_args.kwargs

        assert kwargs["identity"] == SsoIdentity(user_id="user.one")
        assert kwargs["ip_address"] == "testclient"
        assert kwargs["user_agent"] == "pytest"

        user_manager.get_current_user = mocker.AsyncMock(return_value=_current_user(is_active=True, is_admin=True))
        response = client.get("/auth/me", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is True
        assert response.json()["is_admin"] is True

        user_manager.get_current_user = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.get("/auth/me", headers=_HEADERS)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Runtime error"

    def test_get_current_user_requires_token(self, mocker, client, token_verifier, user_manager):
        response = client.get("/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.json()["code"] == "invalid_token"

        token_verifier.verify = mocker.MagicMock(side_effect=AuthError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=AuthErrorCode.INVALID_TOKEN,
            detail="Invalid service token"
        ))
        response = client.get("/auth/me", headers=_HEADERS)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": "Invalid service token", "code": "invalid_token"}
        user_manager.get_current_user.assert_not_awaited()
