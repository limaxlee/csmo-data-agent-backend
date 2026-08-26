import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.constants import HEALTHY_STATUS, UNHEALTHY_STATUS
from data_agent.routers.health import (
    _ping_db,
    check_db_status,
    check_object_storage_status,
    get_object_storage,
    router,
)


class TestHealthRoutes:
    @pytest.fixture
    def object_storage(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def client(self, object_storage):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_object_storage] = lambda: object_storage
        return TestClient(app)

    def test_get_object_storage(self, mocker):
        request = mocker.MagicMock()
        storage = mocker.MagicMock()
        request.app.state.object_storage = storage

        assert get_object_storage(request) is storage

    def test__ping_db(self, mocker):
        connection = mocker.MagicMock()
        connection.execute = mocker.AsyncMock()
        connection.close = mocker.AsyncMock()
        connect = mocker.patch(
            "data_agent.routers.health.asyncpg.connect",
            new=mocker.AsyncMock(return_value=connection)
        )

        asyncio.run(_ping_db())

        assert connect.await_args.kwargs["user"] == "postgres"
        connection.execute.assert_awaited_once_with("SELECT 1")
        connection.close.assert_awaited_once()

        # The connection is closed even when the query itself fails.
        connection.execute = mocker.AsyncMock(side_effect=Exception("boom"))
        connection.close = mocker.AsyncMock()
        with pytest.raises(Exception, match="boom"):
            asyncio.run(_ping_db())
        connection.close.assert_awaited_once()

    def test_check_db_status(self, mocker):
        mocker.patch("data_agent.routers.health._ping_db", new=mocker.AsyncMock())
        assert asyncio.run(check_db_status()) == HEALTHY_STATUS

        # Any failure, including the timeout, degrades to unhealthy instead of raising.
        mocker.patch("data_agent.routers.health._ping_db", new=mocker.AsyncMock(side_effect=Exception("boom")))
        assert asyncio.run(check_db_status()) == UNHEALTHY_STATUS

    def test_check_object_storage_status(self, mocker, object_storage):
        object_storage.list_paginated_objects = mocker.AsyncMock(return_value=["a"])
        assert asyncio.run(check_object_storage_status(object_storage)) == HEALTHY_STATUS
        assert object_storage.list_paginated_objects.await_args.kwargs["max_items"] == 1

        # list_paginated_objects returns None on its own internal failures.
        object_storage.list_paginated_objects = mocker.AsyncMock(return_value=None)
        assert asyncio.run(check_object_storage_status(object_storage)) == UNHEALTHY_STATUS

        object_storage.list_paginated_objects = mocker.AsyncMock(side_effect=Exception("boom"))
        assert asyncio.run(check_object_storage_status(object_storage)) == UNHEALTHY_STATUS

    def test_check_health(self, mocker, client):
        mocker.patch("data_agent.routers.health.check_db_status", new=mocker.AsyncMock(return_value=HEALTHY_STATUS))
        mocker.patch(
            "data_agent.routers.health.check_object_storage_status",
            new=mocker.AsyncMock(return_value=UNHEALTHY_STATUS)
        )

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "server_status": HEALTHY_STATUS,
            "db_status": HEALTHY_STATUS,
            "object_storage_status": UNHEALTHY_STATUS,
        }

        # Reaching the endpoint at all means the server is up, so server_status is a constant.
        mocker.patch("data_agent.routers.health.check_db_status", new=mocker.AsyncMock(return_value=UNHEALTHY_STATUS))
        assert client.get("/health").json()["server_status"] == HEALTHY_STATUS
