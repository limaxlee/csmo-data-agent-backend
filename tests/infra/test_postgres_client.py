import pytest
import asyncio

from common.config import SETTINGS
from data_agent.infra import postgres_client as postgres_client_module
from data_agent.infra.postgres_client import PostgresClient, postgres_dsn


class TestPostgresDsn:
    def test_postgres_dsn(self):
        db = SETTINGS.postgresql_db

        assert postgres_dsn() == f"postgresql+asyncpg://{db.user}@{db.host}:{db.port}/{db.name}"
        assert postgres_dsn("other_db") == f"postgresql+asyncpg://{db.user}@{db.host}:{db.port}/other_db"


class TestPostgresClient:
    @pytest.fixture
    def connection(self, mocker):
        connection = mocker.MagicMock()
        connection.execute = mocker.AsyncMock()
        return connection

    @pytest.fixture
    def engine(self, mocker, connection):
        transaction = mocker.MagicMock()
        transaction.__aenter__ = mocker.AsyncMock(return_value=connection)
        transaction.__aexit__ = mocker.AsyncMock(return_value=False)

        engine = mocker.MagicMock()
        engine.begin = mocker.MagicMock(return_value=transaction)
        engine.dispose = mocker.AsyncMock()
        return engine

    @pytest.fixture
    def create_engine(self, mocker, engine):
        return mocker.patch.object(postgres_client_module, "create_async_engine", return_value=engine)

    @pytest.fixture
    def client(self, create_engine):
        return PostgresClient()

    def test_init(self, create_engine, engine):
        client = PostgresClient()

        assert client._engine is engine
        assert create_engine.call_args.args == (postgres_dsn(),)
        assert create_engine.call_args.kwargs["pool_pre_ping"] is True

        PostgresClient(db_name="other_db")
        assert create_engine.call_args.args == (postgres_dsn("other_db"),)

    def test_execute(self, client, connection):
        asyncio.run(client.execute("UPDATE t SET a = :a", {"a": 1}))

        statement, params = connection.execute.await_args.args
        assert str(statement) == "UPDATE t SET a = :a"
        assert params == {"a": 1}

        asyncio.run(client.execute("DELETE FROM t"))
        assert connection.execute.await_args.args[1] == {}

    def test_fetch_one(self, mocker, client, connection):
        result = mocker.MagicMock()
        result.mappings.return_value.first.return_value = {"ping": 1}
        connection.execute = mocker.AsyncMock(return_value=result)

        assert asyncio.run(client.fetch_one("SELECT 1 AS ping")) == {"ping": 1}
        assert str(connection.execute.await_args.args[0]) == "SELECT 1 AS ping"

        result.mappings.return_value.first.return_value = None
        assert asyncio.run(client.fetch_one("SELECT 1 AS ping")) is None

    def test_fetch_all(self, mocker, client, connection):
        result = mocker.MagicMock()
        result.mappings.return_value.all.return_value = [{"session_id": "session-1"}, {"session_id": "session-2"}]
        connection.execute = mocker.AsyncMock(return_value=result)

        rows = asyncio.run(client.fetch_all("SELECT session_id FROM t WHERE uid = :uid", {"uid": "user-1"}))

        assert rows == [{"session_id": "session-1"}, {"session_id": "session-2"}]
        assert connection.execute.await_args.args[1] == {"uid": "user-1"}

        result.mappings.return_value.all.return_value = []
        assert asyncio.run(client.fetch_all("SELECT session_id FROM t")) == []

    def test_propagates_query_errors(self, mocker, client, connection):
        connection.execute = mocker.AsyncMock(side_effect=Exception("boom"))

        with pytest.raises(Exception, match="boom"):
            asyncio.run(client.fetch_one("SELECT 1"))

    def test_close(self, client, engine):
        asyncio.run(client.close())

        engine.dispose.assert_awaited_once()
