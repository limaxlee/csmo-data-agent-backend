import pytest

from common.constants import HEALTH_CHECK_TIMEOUT
from data_agent.services.health_checker import HealthChecker


class TestHealthChecker:
    @pytest.fixture
    def db_client(self, mocker):
        db_client = mocker.MagicMock()
        db_client.fetch_one = mocker.AsyncMock(return_value={"ping": 1})
        return db_client

    @pytest.fixture
    def object_storage(self, mocker):
        storage = mocker.MagicMock()
        storage.head_bucket = mocker.AsyncMock(return_value=True)
        return storage

    @pytest.fixture
    def checker(self, db_client, object_storage):
        return HealthChecker(
            db_client=db_client,
            object_storage=object_storage,
            timeout_seconds=0.05
        )

    def test_default_timeout(self, db_client, object_storage):
        checker = HealthChecker(
            db_client=db_client,
            object_storage=object_storage
        )

        assert checker._timeout_seconds == HEALTH_CHECK_TIMEOUT

    @pytest.mark.asyncio
    async def test_check_postgresql(self, mocker, db_client, checker):
        assert await checker.check_postgresql() is True
        db_client.fetch_one.assert_awaited_once_with("SELECT 1 AS ping")

        db_client.fetch_one = mocker.AsyncMock(return_value={"ping": 0})
        assert await checker.check_postgresql() is False

        db_client.fetch_one = mocker.AsyncMock(return_value=None)
        assert await checker.check_postgresql() is False

        db_client.fetch_one = mocker.AsyncMock(side_effect=OSError("Connection refused"))
        assert await checker.check_postgresql() is False

        db_client.fetch_one = mocker.AsyncMock( side_effect=TimeoutError)
        assert await checker.check_postgresql() is False

    @pytest.mark.asyncio
    async def test_check_object_storage(self, mocker, object_storage, checker):
        assert await checker.check_object_storage() is True
        object_storage.head_bucket.assert_awaited_once_with()

        object_storage.head_bucket = mocker.AsyncMock(return_value=False)
        assert await checker.check_object_storage() is False

        object_storage.head_bucket = mocker.AsyncMock(side_effect=OSError("Connection refused"))
        assert await checker.check_object_storage() is False

        object_storage.head_bucket = mocker.AsyncMock(side_effect=TimeoutError)
        assert await checker.check_object_storage() is False
