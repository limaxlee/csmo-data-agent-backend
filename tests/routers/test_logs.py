import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from data_agent.routers import logs as logs_router_module
from data_agent.routers.logs import router


class TestLogsRoutes:
    @pytest.fixture
    def client(self):
        app = FastAPI()
        app.include_router(router)
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
