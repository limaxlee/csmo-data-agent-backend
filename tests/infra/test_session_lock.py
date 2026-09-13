import pytest
import asyncio

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
    def lock_repository(self, db_client):
        return SessionLockRepository(db_client=db_client)

    def test_initialize_resets_running_locks(self, db_client, lock_repository):
        asyncio.run(lock_repository.initialize())

        statements = [call.args[0] for call in db_client.execute.await_args_list]
        assert any("CREATE TABLE IF NOT EXISTS session_run_locks" in stmt for stmt in statements)
        assert any("DROP COLUMN IF EXISTS lease_expires_at" in stmt for stmt in statements)
        reset_call = next(
            call for call in db_client.execute.await_args_list if "UPDATE session_run_locks" in call.args[0]
        )
        assert reset_call.args[1] == {"idle": RunState.IDLE, "running": RunState.RUNNING}

    def test_initialize_skips_reset_when_disabled(self, db_client):
        lock_repository = SessionLockRepository(db_client=db_client, reset_on_startup=False)

        asyncio.run(lock_repository.initialize())

        statements = [call.args[0] for call in db_client.execute.await_args_list]
        assert any("CREATE TABLE IF NOT EXISTS session_run_locks" in stmt for stmt in statements)
        assert not any("UPDATE session_run_locks" in stmt for stmt in statements)

    def test_reset_all(self, db_client, lock_repository):
        asyncio.run(lock_repository.reset_all())

        query, params = db_client.execute.await_args.args
        assert "SET run_state = :idle" in query
        assert "WHERE run_state = :running" in query
        assert params == {"idle": RunState.IDLE, "running": RunState.RUNNING}

    def test_try_acquire(self, mocker, db_client, lock_repository):
        db_client.fetch_one = mocker.AsyncMock(return_value={"session_id": "session-1"})
        assert asyncio.run(lock_repository.try_acquire("app", "user-1", "session-1")) is True

        query, params = db_client.fetch_one.await_args.args
        assert "ON CONFLICT (app_name, user_id, session_id) DO UPDATE" in query
        assert "WHERE session_run_locks.run_state = :idle" in query
        assert "lease" not in query
        assert params["app"] == "app"
        assert params["uid"] == "user-1"
        assert params["sid"] == "session-1"

        db_client.fetch_one = mocker.AsyncMock(return_value=None)
        assert asyncio.run(lock_repository.try_acquire("app", "user-1", "session-1")) is False

    def test_release(self, mocker, db_client, lock_repository):
        assert asyncio.run(lock_repository.release("app", "user-1", "session-1")) is True

        query, params = db_client.execute.await_args.args
        assert "SET run_state = :idle" in query
        assert "lease" not in query
        assert params["sid"] == "session-1"

        db_client.execute = mocker.AsyncMock(side_effect=Exception("DB down"))
        assert asyncio.run(lock_repository.release("app", "user-1", "session-1")) is False

    def test_get_run_state(self, mocker, db_client, lock_repository):
        db_client.fetch_one = mocker.AsyncMock(return_value={"run_state": "running"})
        assert asyncio.run(lock_repository.get_run_state("app", "user-1", "session-1")) == RunState.RUNNING

        query, params = db_client.fetch_one.await_args.args
        assert "lease" not in query
        assert params["sid"] == "session-1"

        db_client.fetch_one = mocker.AsyncMock(return_value={"run_state": "idle"})
        assert asyncio.run(lock_repository.get_run_state("app", "user-1", "session-1")) == RunState.IDLE

        db_client.fetch_one = mocker.AsyncMock(return_value=None)
        assert asyncio.run(lock_repository.get_run_state("app", "user-1", "session-1")) == RunState.IDLE

    def test_get_run_states(self, mocker, db_client, lock_repository):
        assert asyncio.run(lock_repository.get_run_states("app", "user-1", [])) == {}
        db_client.fetch_all.assert_not_awaited()

        db_client.fetch_all = mocker.AsyncMock(return_value=[{"session_id": "session-2"}])
        result = asyncio.run(lock_repository.get_run_states("app", "user-1", ["session-1", "session-2"]))
        assert result == {"session-1": RunState.IDLE, "session-2": RunState.RUNNING}

        query, params = db_client.fetch_all.await_args.args
        assert "lease" not in query
        assert params["sids"] == ["session-1", "session-2"]
        assert params["running"] == RunState.RUNNING

    def test_delete(self, db_client, lock_repository):
        asyncio.run(lock_repository.delete("app", "user-1", "session-1"))

        query, params = db_client.execute.await_args.args
        assert "DELETE FROM session_run_locks" in query
        assert params["app"] == "app"
        assert params["uid"] == "user-1"
        assert params["sid"] == "session-1"
