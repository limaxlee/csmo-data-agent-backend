import pytest
from datetime import datetime, timezone
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette import status

from common.constants import AuthErrorCode, MAX_USER_AGENT_LENGTH
from data_agent.exceptions import AuthError, register_exception_handlers
from data_agent.routers.dependencies import (
    ActiveUserDep, AdminDep, IdentityDep, get_client_ip, get_identity, get_token_verifier,
    get_user_agent, get_user_manager, require_active_user, require_admin, require_session_owner
)
from data_agent.schemas import SsoIdentity, UserInfo

_HEADERS = {"Authorization": "Bearer token-1"}


def _identity(user_id="user.one"):
    return SsoIdentity(user_id=user_id)


def _user(user_id="user.one", **overrides):
    return UserInfo(
        user_id=user_id,
        is_active=True,
        created_at=datetime(2026, 11, 22, 10, 15, tzinfo=timezone.utc),
        **overrides
    )


class TestDependencies:
    @pytest.fixture
    def token_verifier(self, mocker):
        verifier = mocker.MagicMock()
        verifier.verify = mocker.MagicMock(return_value=_identity())
        return verifier

    @pytest.fixture
    def user_manager(self, mocker):
        manager = mocker.MagicMock()
        manager.authorize = mocker.AsyncMock(return_value=_user())
        manager.is_admin = mocker.AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def client(self, token_verifier, user_manager):
        app = FastAPI()
        register_exception_handlers(app)
        app.dependency_overrides[get_token_verifier] = lambda: token_verifier
        app.dependency_overrides[get_user_manager] = lambda: user_manager

        @app.get("/identity")
        async def identity(identity: IdentityDep):
            return {"user_id": identity.user_id}

        @app.get("/active")
        async def active(user: ActiveUserDep):
            return {"user_id": user.user_id}

        @app.get("/users/{user_id}", dependencies=[Depends(require_session_owner)])
        async def owner(user_id: str):
            return {"user_id": user_id}

        @app.get("/admin")
        async def admin(admin: AdminDep):
            return {"user_id": admin.user_id}

        return TestClient(app)

    def test_get_token_verifier(self, mocker):
        request = mocker.MagicMock()
        verifier = mocker.MagicMock()
        request.app.state.token_verifier = verifier

        assert get_token_verifier(request) is verifier

    def test_get_user_manager(self, mocker):
        request = mocker.MagicMock()
        manager = mocker.MagicMock()
        request.app.state.user_manager = manager

        assert get_user_manager(request) is manager

    def test_get_client_ip(self, mocker):
        request = mocker.MagicMock()
        request.client.host = "10.0.0.1"

        assert get_client_ip(request) == "10.0.0.1"

        request.client = None

        assert get_client_ip(request) is None

    def test_get_user_agent(self, mocker):
        request = mocker.MagicMock()
        request.headers = {"user-agent": "pytest"}

        assert get_user_agent(request) == "pytest"

        request.headers = {"user-agent": "a" * (MAX_USER_AGENT_LENGTH + 10)}

        assert get_user_agent(request) == "a" * MAX_USER_AGENT_LENGTH

        request.headers = {}

        assert get_user_agent(request) is None

    def test_get_identity(self, token_verifier):
        assert get_identity(token_verifier, "Bearer token-1") == _identity()
        token_verifier.verify.assert_called_once_with("token-1")

        for authorization in [None, "", "token-1", "Basic token-1", "bearer token-1", "Bearer ", "Bearer    "]:
            with pytest.raises(AuthError) as error:
                get_identity(token_verifier, authorization)

            assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert error.value.code == AuthErrorCode.INVALID_TOKEN

        token_verifier.verify.assert_called_once()

    @pytest.mark.asyncio
    async def test_require_active_user(self, mocker, user_manager):
        request = mocker.MagicMock()
        request.client.host = "10.0.0.1"
        request.headers = {"user-agent": "pytest"}

        user = await require_active_user(request, _identity(), user_manager)

        assert user == _user()
        user_manager.authorize.assert_awaited_once_with(
            identity=_identity(),
            ip_address="10.0.0.1",
            user_agent="pytest"
        )

    @pytest.mark.asyncio
    async def test_require_session_owner(self):
        assert await require_session_owner("user.one", _user()) is None

        for user_id in ["user.two", "User.One", ""]:
            with pytest.raises(AuthError) as error:
                await require_session_owner(user_id, _user())

            assert error.value.status_code == status.HTTP_403_FORBIDDEN
            assert error.value.code == AuthErrorCode.USER_MISMATCH

    @pytest.mark.asyncio
    async def test_require_admin(self, mocker, user_manager):
        assert await require_admin(_identity(), user_manager) == _identity()
        user_manager.is_admin.assert_awaited_once_with("user.one")

        user_manager.is_admin = mocker.AsyncMock(return_value=False)

        with pytest.raises(AuthError) as error:
            await require_admin(_identity(), user_manager)

        assert error.value.status_code == status.HTTP_403_FORBIDDEN
        assert error.value.code == AuthErrorCode.ADMIN_REQUIRED

    def test_missing_token(self, client, token_verifier, user_manager):
        for path in ["/identity", "/active", "/users/user.one", "/admin"]:
            response = client.get(path)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.headers["www-authenticate"] == "Bearer"
            assert response.json() == {
                "detail": "Missing or invalid Authorization header",
                "code": "invalid_token"
            }

        token_verifier.verify.assert_not_called()
        user_manager.authorize.assert_not_awaited()
        user_manager.is_admin.assert_not_awaited()

    def test_invalid_token(self, mocker, client, token_verifier, user_manager):
        token_verifier.verify = mocker.MagicMock(side_effect=AuthError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=AuthErrorCode.INVALID_TOKEN,
            detail="Invalid service token"
        ))

        for path in ["/identity", "/active", "/users/user.one", "/admin"]:
            response = client.get(path, headers=_HEADERS)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json() == {"detail": "Invalid service token", "code": "invalid_token"}

        user_manager.authorize.assert_not_awaited()
        user_manager.is_admin.assert_not_awaited()

    def test_identity(self, client, token_verifier):
        response = client.get("/identity", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"user_id": "user.one"}
        token_verifier.verify.assert_called_once_with("token-1")

    def test_active_user(self, mocker, client, user_manager):
        response = client.get("/active", headers={**_HEADERS, "User-Agent": "pytest"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"user_id": "user.one"}
        assert user_manager.authorize.await_args.kwargs["identity"] == _identity()
        assert user_manager.authorize.await_args.kwargs["user_agent"] == "pytest"

        user_manager.authorize = mocker.AsyncMock(side_effect=AuthError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=AuthErrorCode.ACCOUNT_INACTIVE,
            detail="This account is waiting for approval"
        ))

        response = client.get("/active", headers=_HEADERS)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "www-authenticate" not in response.headers
        assert response.json() == {
            "detail": "This account is waiting for approval",
            "code": "account_inactive"
        }

    def test_session_owner(self, client):
        response = client.get("/users/user.one", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"user_id": "user.one"}

        response = client.get("/users/user.two", headers=_HEADERS)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "This address belongs to another user", "code": "user_mismatch"}

    def test_admin(self, mocker, client, user_manager):
        response = client.get("/admin", headers=_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"user_id": "user.one"}

        user_manager.is_admin = mocker.AsyncMock(return_value=False)

        response = client.get("/admin", headers=_HEADERS)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "Administrator access is required", "code": "admin_required"}
