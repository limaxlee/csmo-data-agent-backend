import pytest
import asyncio

from common.constants import HEALTH_CHECK_TIMEOUT
from data_agent.services.health import HealthChecker


class TestHealthChecker:
    @pytest.fixture
    def db_client(self, mocker):
        db_client = mocker.MagicMock()
        db_client.fetch_one = mocker.AsyncMock(return_value={"ping": 1})
        return db_client

    @pytest.fixture
    def object_storage(self, mocker):
        storage = mocker.MagicMock()
        storage.bucket = "bucket"
        storage.client.head_bucket = mocker.AsyncMock(return_value={})
        return storage

    @pytest.fixture
    def checker(self, db_client, object_storage):
        return HealthChecker(db_client=db_client, object_storage=object_storage, timeout_seconds=0.05)

    def test_default_timeout(self, db_client, object_storage):
        checker = HealthChecker(db_client=db_client, object_storage=object_storage)

        assert checker._timeout_seconds == HEALTH_CHECK_TIMEOUT

    def test_check_postgres(self, mocker, db_client, checker):
        assert asyncio.run(checker.check_postgres()) is True
        assert db_client.fetch_one.await_args.args == ("SELECT 1 AS ping",)

        db_client.fetch_one = mocker.AsyncMock(return_value={"ping": 0})
        assert asyncio.run(checker.check_postgres()) is False

        db_client.fetch_one = mocker.AsyncMock(return_value=None)
        assert asyncio.run(checker.check_postgres()) is False

        db_client.fetch_one = mocker.AsyncMock(side_effect=OSError("connection refused"))
        assert asyncio.run(checker.check_postgres()) is False

    def test_check_postgres_times_out(self, mocker, db_client, checker):
        async def _hang(query):
            await asyncio.sleep(5)
            return {"ping": 1}

        db_client.fetch_one = mocker.AsyncMock(side_effect=_hang)

        assert asyncio.run(checker.check_postgres()) is False

    def test_check_storage(self, mocker, object_storage, checker):
        assert asyncio.run(checker.check_storage()) is True
        object_storage.client.head_bucket.assert_awaited_once_with(Bucket="bucket")

        object_storage.client.head_bucket = mocker.AsyncMock(side_effect=OSError("connection refused"))
        assert asyncio.run(checker.check_storage()) is False

        type(object_storage).client = mocker.PropertyMock(side_effect=RuntimeError("not connected"))
        assert asyncio.run(checker.check_storage()) is False

    def test_check_storage_times_out(self, mocker, object_storage, checker):
        async def _hang(**kwargs):
            await asyncio.sleep(5)
            return {}

        object_storage.client.head_bucket = mocker.AsyncMock(side_effect=_hang)

        assert asyncio.run(checker.check_storage()) is False
