import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from common.constants import AuthErrorCode
from data_agent.exceptions import AuthError, handle_auth_error, register_exception_handlers


class TestAuthError:
    def test_auth_error(self):
        error = AuthError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=AuthErrorCode.ADMIN_REQUIRED,
            detail="Administrator access is required"
        )

        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.code == "admin_required"
        assert error.detail == "Administrator access is required"
        assert str(error) == "Administrator access is required"

    @pytest.mark.asyncio
    async def test_handle_auth_error(self, mocker):
        response = await handle_auth_error(
            mocker.MagicMock(),
            AuthError(status.HTTP_401_UNAUTHORIZED, AuthErrorCode.INVALID_TOKEN, "Invalid service token")
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.headers["www-authenticate"] == "Bearer"
        assert json.loads(response.body) == {"detail": "Invalid service token", "code": "invalid_token"}

        response = await handle_auth_error(
            mocker.MagicMock(),
            AuthError(status.HTTP_403_FORBIDDEN, AuthErrorCode.ACCOUNT_INACTIVE, "Waiting for approval")
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "www-authenticate" not in response.headers
        assert json.loads(response.body) == {"detail": "Waiting for approval", "code": "account_inactive"}

    def test_register_exception_handlers(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/forbidden")
        async def forbidden():
            raise AuthError(status.HTTP_403_FORBIDDEN, AuthErrorCode.USER_MISMATCH, "Another user")

        response = TestClient(app).get("/forbidden")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "Another user", "code": "user_mismatch"}
