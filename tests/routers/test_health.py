import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from data_agent.routers import health as health_router_module
from data_agent.routers.health import router


class TestHealthRoutes:
    @pytest.fixture
    def client(self):
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_check_health(self, mocker, client):
        mocker.patch.object(
            health_router_module,
            "check_postgres_health",
            new=mocker.AsyncMock(return_value=True)
        )
        mocker.patch.object(
            health_router_module,
            "check_storage_health",
            new=mocker.AsyncMock(return_value=True)
        )

        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "server_status": "healthy",
            "postgresql_db_status": "healthy",
            "object_storage_status": "healthy"
        }

        mocker.patch.object(
            health_router_module,
            "check_postgres_health",
            new=mocker.AsyncMock(return_value=False)
        )
        mocker.patch.object(
            health_router_module,
            "check_storage_health",
            new=mocker.AsyncMock(return_value=False)
        )

        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "server_status": "healthy",
            "postgresql_db_status": "unhealthy",
            "object_storage_status": "unhealthy"
        }

        mocker.patch.object(
            health_router_module,
            "check_postgres_health",
            new=mocker.AsyncMock(side_effect=Exception("Runtime error"))
        )

        response = client.get("/health")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Runtime error"
