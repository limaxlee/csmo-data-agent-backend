import pytest

from common.config import SETTINGS
from common.constants import HEALTH_CHECK_TIMEOUT
from data_agent.utils.health import check_postgres_health, check_storage_health


class TestHealthUtils:
    @pytest.mark.asyncio
    async def test_check_postgres_health(self, mocker):
        connection = mocker.AsyncMock()
        connection.fetchval.return_value = 1

        connect_mock = mocker.patch("data_agent.utils.health.connect", new=mocker.AsyncMock(return_value=connection))
        result = await check_postgres_health()
        assert result is True

        connect_mock.assert_awaited_once_with(
            host=SETTINGS.postgresql_db.host,
            port=SETTINGS.postgresql_db.port,
            database=SETTINGS.postgresql_db.name,
            user=SETTINGS.postgresql_db.user,
            timeout=HEALTH_CHECK_TIMEOUT
        )
        connection.fetchval.assert_awaited_once_with("SELECT 1;")
        connection.close.assert_awaited_once()

        connect_mock.reset_mock()
        connect_mock.side_effect = OSError()

        result = await check_postgres_health()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_storage_health(self, mocker):
        client = mocker.AsyncMock()

        client_context = mocker.MagicMock()
        client_context.__aenter__ = mocker.AsyncMock(return_value=client)
        client_context.__aexit__ = mocker.AsyncMock(return_value=None)

        session = mocker.MagicMock()
        session.create_client.return_value = client_context

        get_session_mock = mocker.patch("data_agent.utils.health.get_session", return_value=session)

        result = await check_storage_health()
        assert result is True

        get_session_mock.assert_called_once()
        session.create_client.assert_called_once()

        client.head_bucket.assert_awaited_once_with(Bucket=SETTINGS.object_storage.bucket)

        _, kwargs = session.create_client.call_args

        assert kwargs["endpoint_url"] == SETTINGS.object_storage.endpoint
        assert kwargs["aws_access_key_id"] == SETTINGS.object_storage.access_key
        assert kwargs["aws_secret_access_key"] == SETTINGS.object_storage.secret_key

        client.head_bucket.reset_mock()
        client.head_bucket.side_effect = OSError()
        result = await check_storage_health()

        assert result is False
