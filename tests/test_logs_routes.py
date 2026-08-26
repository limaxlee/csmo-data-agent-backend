import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from data_agent.routers.logs import router


class TestLogsRoutes:
    @pytest.fixture
    def client(self):
        app = FastAPI()
        app.include_router(router)
        return TestClient(app, raise_server_exceptions=False)

    def test_download_logs(self, mocker, client):
        mocker.patch("data_agent.routers.logs.get_logs_zip_file", new=mocker.AsyncMock(return_value=b"zip bytes"))

        response = client.get("/logs")

        assert response.status_code == 200
        assert response.content == b"zip bytes"
        assert response.headers["content-type"] == "application/zip"
        assert response.headers["content-disposition"].startswith("attachment; filename=")
        assert response.headers["content-disposition"].endswith('.zip"')

        # No logs on disk. The handler raises a 404, but its own `except Exception`
        # catches that HTTPException and re-raises it as a 500 -- so the client sees
        # 500, not 404. This asserts the current behaviour; the endpoint should
        # re-raise HTTPException instead of swallowing it.
        mocker.patch("data_agent.routers.logs.get_logs_zip_file", new=mocker.AsyncMock(return_value=None))
        response = client.get("/logs")
        assert response.status_code == 500
        assert response.json()["detail"] == "404: No log files found"

        mocker.patch("data_agent.routers.logs.get_logs_zip_file", new=mocker.AsyncMock(side_effect=Exception("boom")))
        response = client.get("/logs")
        assert response.status_code == 500
        assert response.json()["detail"] == "boom"
