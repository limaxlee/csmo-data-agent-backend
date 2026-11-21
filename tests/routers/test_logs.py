import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from data_agent.exceptions import register_exception_handlers
from data_agent.routers import logs as logs_router_module
from data_agent.routers.dependencies import get_token_verifier, get_user_manager, require_admin
from data_agent.routers.logs import router
from data_agent.schemas import SsoIdentity


class TestLogsRoutes:
    @pytest.fixture
    def client(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[require_admin] = lambda: SsoIdentity(user_id="admin.one")
        return TestClient(app)

    def test_download_logs(self, mocker, client):
        mocker.patch.object(
            logs_router_module,
            "get_logs_zip_file",
            new=mocker.AsyncMock(return_value=b"zip-bytes")
        )

        response = client.get("/logs")

        assert response.status_code == status.HTTP_200_OK
        assert response.content == b"zip-bytes"
        assert response.headers["content-type"] == "application/zip"
        assert response.headers["content-disposition"].endswith('.zip"')

        mocker.patch.object(logs_router_module, "get_logs_zip_file", new=mocker.AsyncMock(return_value=None))

        response = client.get("/logs")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "No log files found" in response.json()["detail"]

        mocker.patch.object(
            logs_router_module,
            "get_logs_zip_file",
            new=mocker.AsyncMock(side_effect=Exception("Runtime error"))
        )

        response = client.get("/logs")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Runtime error"

    def test_download_logs_requires_admin(self, mocker):
        get_logs_zip_file = mocker.patch.object(
            logs_router_module,
            "get_logs_zip_file",
            new=mocker.AsyncMock(return_value=b"zip-bytes")
        )

        token_verifier = mocker.MagicMock()
        token_verifier.verify = mocker.MagicMock(return_value=SsoIdentity(user_id="user.one"))

        user_manager = mocker.MagicMock()
        user_manager.is_admin = mocker.AsyncMock(return_value=False)

        app = FastAPI()
        app.include_router(router)
        register_exception_handlers(app)
        app.dependency_overrides[get_token_verifier] = lambda: token_verifier
        app.dependency_overrides[get_user_manager] = lambda: user_manager
        client = TestClient(app)
        headers = {"Authorization": "Bearer token-1"}

        response = client.get("/logs")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["code"] == "invalid_token"

        response = client.get("/logs", headers=headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["code"] == "admin_required"
        get_logs_zip_file.assert_not_awaited()

        user_manager.is_admin = mocker.AsyncMock(return_value=True)
        response = client.get("/logs", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.content == b"zip-bytes"
