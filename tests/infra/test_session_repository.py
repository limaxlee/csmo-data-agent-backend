import pytest
from datetime import datetime, timezone

from common.constants import RunState, SessionStateFields, DEFAULT_SESSION_LIMIT
from data_agent.infra.session_repository import SessionRepository

_NOW = datetime(2026, 11, 24, 10, 15, tzinfo=timezone.utc)


def _session_filters(**overrides):
    filters = {
        "app": "app",
        "uid": None,
        "search": None,
        "created_from": None,
        "created_to": None,
        "updated_from": None,
        "updated_to": None,
        "title": SessionStateFields.TITLE
    }
    filters.update(overrides)
    return filters


class TestSessionRepository:
    @pytest.fixture
    def db_client(self, mocker):
        db_client = mocker.MagicMock()
        db_client.execute = mocker.AsyncMock()
        db_client.fetch_one = mocker.AsyncMock(return_value=None)
        db_client.fetch_all = mocker.AsyncMock(return_value=[])
        return db_client

    @pytest.fixture
    def session_repository(self, db_client):
        return SessionRepository(db_client=db_client)

    @pytest.mark.asyncio
    async def test_list_sessions(self, mocker, db_client, session_repository):
        assert await session_repository.list_sessions("app") == []

        query, params = db_client.fetch_all.await_args.args

        assert "s.id AS session_id" in query
        assert "s.state ->> CAST(:title AS TEXT) AS session_title" in query
        assert "s.create_time AT TIME ZONE 'UTC' AS created_at" in query
        assert "s.update_time AT TIME ZONE 'UTC' AS last_update_time" in query
        assert "COALESCE(l.run_state, :idle) AS run_state" in query
        assert "FROM sessions s" in query
        assert "LEFT JOIN session_run_locks l" in query
        assert "ON l.app_name = s.app_name AND l.user_id = s.user_id AND l.session_id = s.id" in query
        assert "WHERE s.app_name = :app" in query
        assert "CAST(:uid AS TEXT) IS NULL OR lower(s.user_id) = lower(CAST(:uid AS TEXT))" in query
        assert "strpos(lower(concat_ws(' ', s.user_id, s.state ->> CAST(:title AS TEXT), s.id))" in query
        assert "s.create_time AT TIME ZONE 'UTC' >= CAST(:created_from AS TIMESTAMPTZ)" in query
        assert "s.create_time AT TIME ZONE 'UTC' < CAST(:created_to AS TIMESTAMPTZ)" in query
        assert "s.update_time AT TIME ZONE 'UTC' >= CAST(:updated_from AS TIMESTAMPTZ)" in query
        assert "s.update_time AT TIME ZONE 'UTC' < CAST(:updated_to AS TIMESTAMPTZ)" in query
        assert "ORDER BY s.create_time DESC, s.id" in query
        assert "LIMIT :limit OFFSET :offset" in query

        # The agent framework's tables are only read.
        for statement in ["INSERT", "UPDATE", "DELETE"]:
            assert statement not in query

        assert params == _session_filters(idle=RunState.IDLE, limit=DEFAULT_SESSION_LIMIT, offset=0)

        sessions = [{"user_id": "user.one", "session_id": "session-1", "run_state": "running"}]
        db_client.fetch_all = mocker.AsyncMock(return_value=sessions)

        result = await session_repository.list_sessions(
            "app",
            user_id="User.One",
            search="defect",
            created_from=_NOW,
            created_to=_NOW,
            updated_from=_NOW,
            updated_to=_NOW,
            limit=10,
            offset=20
        )

        assert result == sessions
        assert db_client.fetch_all.await_args.args[1] == _session_filters(
            uid="User.One",
            search="defect",
            created_from=_NOW,
            created_to=_NOW,
            updated_from=_NOW,
            updated_to=_NOW,
            idle=RunState.IDLE,
            limit=10,
            offset=20
        )

    @pytest.mark.asyncio
    async def test_count_sessions(self, mocker, db_client, session_repository):
        db_client.fetch_one = mocker.AsyncMock(return_value={"total": 0})

        assert await session_repository.count_sessions("app") == 0

        query, params = db_client.fetch_one.await_args.args

        assert "SELECT count(*) AS total" in query
        assert "FROM sessions s" in query
        assert "WHERE s.app_name = :app" in query
        assert "CAST(:uid AS TEXT) IS NULL OR lower(s.user_id) = lower(CAST(:uid AS TEXT))" in query
        assert "s.create_time AT TIME ZONE 'UTC' >= CAST(:created_from AS TIMESTAMPTZ)" in query
        assert "s.update_time AT TIME ZONE 'UTC' < CAST(:updated_to AS TIMESTAMPTZ)" in query
        assert "session_run_locks" not in query
        assert "LIMIT" not in query
        assert params == _session_filters()

        db_client.fetch_one = mocker.AsyncMock(return_value={"total": 4})
        total = await session_repository.count_sessions(
            "app",
            user_id="user.one",
            search="defect",
            created_from=_NOW,
            created_to=_NOW,
            updated_from=_NOW,
            updated_to=_NOW
        )

        assert total == 4
        assert db_client.fetch_one.await_args.args[1] == _session_filters(
            uid="user.one",
            search="defect",
            created_from=_NOW,
            created_to=_NOW,
            updated_from=_NOW,
            updated_to=_NOW
        )
