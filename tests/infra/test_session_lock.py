import pytest

from common.constants import RunState
from data_agent.infra.session_lock import SessionLockRepository


class TestSessionLockRepository:
    @pytest.fixture
    def db_client(self, mocker):
        db_client = mocker.MagicMock()
        db_client.execute = mocker.AsyncMock()
        db_client.fetch_one = mocker.AsyncMock(return_value=None)
        db_client.fetch_all = mocker.AsyncMock(return_value=[])
        return db_client

    @pytest.fixture
    def session_lock(self, db_client):
        return SessionLockRepository(db_client=db_client)

    @pytest.mark.asyncio
    async def test_initialize(self, db_client, session_lock):
        await session_lock.initialize()

        assert db_client.execute.await_count == 3

        create_call = db_client.execute.await_args_list[0]
        reset_call = db_client.execute.await_args_list[2]

        assert "CREATE TABLE IF NOT EXISTS session_run_locks" in create_call.args[0]
        assert "run_state  TEXT NOT NULL DEFAULT 'idle'" in create_call.args[0]
        assert "PRIMARY KEY (app_name, user_id, session_id)" in create_call.args[0]

        query, params = reset_call.args

        assert "UPDATE session_run_locks" in query
        assert "SET run_state = :idle" in query
        assert "WHERE run_state = :running" in query
        assert params == {"idle": RunState.IDLE, "running": RunState.RUNNING}

    @pytest.mark.asyncio
    async def test_acquire(self, mocker, db_client, session_lock):
        db_client.fetch_one = mocker.AsyncMock(return_value={"session_id": "session-1"})
        acquired = await session_lock.acquire("app", "user-1", "session-1")

        assert acquired is True

        query, params = db_client.fetch_one.await_args.args

        assert "INSERT INTO session_run_locks" in query
        assert "ON CONFLICT (app_name, user_id, session_id) DO UPDATE" in query
        assert "WHERE session_run_locks.run_state = :idle" in query
        assert "RETURNING session_id" in query
        assert "lease" not in query

        assert params["app"] == "app"
        assert params["uid"] == "user-1"
        assert params["sid"] == "session-1"
        assert params["running"] == RunState.RUNNING
        assert params["idle"] == RunState.IDLE

        db_client.fetch_one = mocker.AsyncMock(return_value=None)
        acquired = await session_lock.acquire("app", "user-1", "session-1")

        assert acquired is False

    @pytest.mark.asyncio
    async def test_release(self, mocker, db_client, session_lock):
        db_client.execute = mocker.AsyncMock(return_value=None)
        released = await session_lock.release("app", "user-1", "session-1")

        assert released is True

        query, params = db_client.execute.await_args.args

        assert "UPDATE session_run_locks" in query
        assert "SET run_state = :idle" in query
        assert "lease" not in query

        assert params["app"] == "app"
        assert params["uid"] == "user-1"
        assert params["sid"] == "session-1"
        assert params["idle"] == RunState.IDLE

        db_client.execute = mocker.AsyncMock(side_effect=Exception("DB down"))
        released = await session_lock.release("app", "user-1", "session-1")

        assert released is False

    @pytest.mark.asyncio
    async def test_get_run_state(self, mocker, db_client, session_lock):
        db_client.fetch_one = mocker.AsyncMock(return_value={"run_state": "running"})
        state = await session_lock.get_run_state("app", "user-1", "session-1")

        assert state == RunState.RUNNING

        query, params = db_client.fetch_one.await_args.args
        assert "SELECT run_state" in query
        assert "FROM session_run_locks" in query
        assert "lease" not in query

        assert params["app"] == "app"
        assert params["uid"] == "user-1"
        assert params["sid"] == "session-1"

        db_client.fetch_one = mocker.AsyncMock(return_value={"run_state": "idle"})
        state = await session_lock.get_run_state("app", "user-1", "session-1")

        assert state == RunState.IDLE

        db_client.fetch_one = mocker.AsyncMock(return_value=None)
        state = await session_lock.get_run_state("app", "user-1", "session-1")

        assert state == RunState.IDLE

    @pytest.mark.asyncio
    async def test_get_run_states(self, mocker, db_client, session_lock):
        result = await session_lock.get_run_states("app", "user-1", [])

        assert result == {}
        db_client.fetch_all.assert_not_awaited()

        db_client.fetch_all = mocker.AsyncMock(return_value=[{"session_id": "session-2"}])

        result = await session_lock.get_run_states("app", "user-1", ["session-1", "session-2"])

        assert result == {"session-1": RunState.IDLE, "session-2": RunState.RUNNING}

        query, params = db_client.fetch_all.await_args.args

        assert "FROM session_run_locks" in query
        assert "lease" not in query

        assert params["app"] == "app"
        assert params["uid"] == "user-1"
        assert params["sids"] == ["session-1", "session-2"]
        assert params["running"] == RunState.RUNNING

    @pytest.mark.asyncio
    async def test_delete(self, db_client, session_lock):
        await session_lock.delete("app", "user-1", "session-1")
        query, params = db_client.execute.await_args.args

        assert "DELETE FROM session_run_locks" in query
        assert "WHERE app_name = :app" in query
        assert "user_id = :uid" in query
        assert "session_id = :sid" in query

        assert params["app"] == "app"
        assert params["uid"] == "user-1"
        assert params["sid"] == "session-1"
