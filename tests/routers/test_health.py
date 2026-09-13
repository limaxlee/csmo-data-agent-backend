import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from data_agent.routers.health import get_health_checker, router


class TestHealthRoutes:
    @pytest.fixture
    def health_checker(self, mocker):
        checker = mocker.MagicMock()
        checker.check_postgres = mocker.AsyncMock(return_value=True)
        checker.check_storage = mocker.AsyncMock(return_value=True)
        return checker

    @pytest.fixture
    def client(self, health_checker):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_health_checker] = lambda: health_checker
        return TestClient(app)

    def test_get_health_checker(self, mocker):
        request = mocker.MagicMock()
        checker = mocker.MagicMock()
        request.app.state.health_checker = checker

        assert get_health_checker(request) is checker

    def test_check_health(self, mocker, client, health_checker):
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "server_status": "healthy",
            "postgresql_db_status": "healthy",
            "object_storage_status": "healthy"
        }
        health_checker.check_postgres.assert_awaited_once()
        health_checker.check_storage.assert_awaited_once()

        health_checker.check_postgres = mocker.AsyncMock(return_value=False)
        health_checker.check_storage = mocker.AsyncMock(return_value=False)

        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "server_status": "healthy",
            "postgresql_db_status": "unhealthy",
            "object_storage_status": "unhealthy"
        }

        health_checker.check_postgres = mocker.AsyncMock(side_effect=Exception("Runtime error"))

        response = client.get("/health")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Runtime error"
