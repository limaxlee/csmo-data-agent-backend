import pytest
from sqlalchemy.engine import make_url

from common.config import SETTINGS
from data_agent.infra import postgresql_client as postgres_client_module
from data_agent.infra.postgresql_client import PostgreSQLClient, postgresql_dsn


class TestPostgreSQLDsn:
    def test_postgres_dsn(self, monkeypatch):
        db = SETTINGS.postgresql_db
        monkeypatch.setattr(db, "password", "")

        assert postgresql_dsn() == f"postgresql+asyncpg://{db.user}@{db.host}:{db.port}/{db.name}"
        assert postgresql_dsn("other_db") == f"postgresql+asyncpg://{db.user}@{db.host}:{db.port}/other_db"

        monkeypatch.setattr(db, "password", "db-password")
        assert postgresql_dsn() == f"postgresql+asyncpg://{db.user}:db-password@{db.host}:{db.port}/{db.name}"

        monkeypatch.setattr(db, "password", "p@ss:word/1 %")
        dsn = postgresql_dsn("other_db")
        assert "p@ss:word/1 %" not in dsn
        assert make_url(dsn).password == "p@ss:word/1 %"
        assert make_url(dsn).host == db.host
        assert make_url(dsn).database == "other_db"


class TestPostgreSQLClient:
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
        return PostgreSQLClient()

    def test_init(self, create_engine, engine):
        client = PostgreSQLClient()

        assert client._engine is engine
        assert create_engine.call_args.args == (postgresql_dsn(),)
        assert create_engine.call_args.kwargs["pool_pre_ping"] is True

        PostgreSQLClient(db_name="other_db")
        assert create_engine.call_args.args == (postgresql_dsn("other_db"),)

    @pytest.mark.asyncio
    async def test_execute(self, client, connection):
        await client.execute("UPDATE t SET a = :a", {"a": 1})

        statement, params = connection.execute.await_args.args
        assert str(statement) == "UPDATE t SET a = :a"
        assert params == {"a": 1}

        await client.execute("DELETE FROM t")
        assert connection.execute.await_args.args[1] == {}

    @pytest.mark.asyncio
    async def test_fetch_one(self, mocker, client, connection):
        result = mocker.MagicMock()
        result.mappings.return_value.first.return_value = {"ping": 1}
        connection.execute = mocker.AsyncMock(return_value=result)

        assert await client.fetch_one("SELECT 1 AS ping") == {"ping": 1}
        assert str(connection.execute.await_args.args[0]) == "SELECT 1 AS ping"

        result.mappings.return_value.first.return_value = None
        assert await client.fetch_one("SELECT 1 AS ping") is None

    @pytest.mark.asyncio
    async def test_fetch_all(self, mocker, client, connection):
        result = mocker.MagicMock()
        result.mappings.return_value.all.return_value = [{"session_id": "session-1"}, {"session_id": "session-2"}]
        connection.execute = mocker.AsyncMock(return_value=result)

        rows = await client.fetch_all("SELECT session_id FROM t WHERE uid = :uid", {"uid": "user-1"})

        assert rows == [{"session_id": "session-1"}, {"session_id": "session-2"}]
        assert connection.execute.await_args.args[1] == {"uid": "user-1"}

        result.mappings.return_value.all.return_value = []
        assert await client.fetch_all("SELECT session_id FROM t") == []

    @pytest.mark.asyncio
    async def test_close(self, client, engine):
        await client.close()

        engine.dispose.assert_awaited_once()
