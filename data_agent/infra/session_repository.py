from datetime import datetime

from common.constants import RunState, SessionStateFields, DEFAULT_SESSION_LIMIT
from data_agent.infra.postgresql_client import PostgreSQLClient

_SESSION_TITLE = "s.state ->> CAST(:title AS TEXT)"

# The agent framework stores both times in UTC, in columns that carry no time zone.
_CREATED_AT = "s.create_time AT TIME ZONE 'UTC'"
_UPDATED_AT = "s.update_time AT TIME ZONE 'UTC'"

_SESSION_FILTERS = f"""
            WHERE s.app_name = :app
              AND (CAST(:uid AS TEXT) IS NULL OR lower(s.user_id) = lower(CAST(:uid AS TEXT)))
              AND (CAST(:search AS TEXT) IS NULL
                   OR strpos(lower(concat_ws(' ', s.user_id, {_SESSION_TITLE}, s.id)),
                             lower(CAST(:search AS TEXT))) > 0)
              AND (CAST(:created_from AS TIMESTAMPTZ) IS NULL OR {_CREATED_AT} >= CAST(:created_from AS TIMESTAMPTZ))
              AND (CAST(:created_to AS TIMESTAMPTZ) IS NULL OR {_CREATED_AT} < CAST(:created_to AS TIMESTAMPTZ))
              AND (CAST(:updated_from AS TIMESTAMPTZ) IS NULL OR {_UPDATED_AT} >= CAST(:updated_from AS TIMESTAMPTZ))
              AND (CAST(:updated_to AS TIMESTAMPTZ) IS NULL OR {_UPDATED_AT} < CAST(:updated_to AS TIMESTAMPTZ))
"""


class SessionRepository:
    # Reads the agent framework's own sessions table. Every change to a session goes through the framework.
    def __init__(self, db_client: PostgreSQLClient):
        self._db = db_client

    async def list_sessions(
            self,
            app_name: str,
            user_id: str | None = None,
            search: str | None = None,
            created_from: datetime | None = None,
            created_to: datetime | None = None,
            updated_from: datetime | None = None,
            updated_to: datetime | None = None,
            limit: int = DEFAULT_SESSION_LIMIT,
            offset: int = 0
    ) -> list[dict]:
        return await self._db.fetch_all(
            f"""
            SELECT s.user_id,
                   s.id AS session_id,
                   {_SESSION_TITLE} AS session_title,
                   {_CREATED_AT} AS created_at,
                   {_UPDATED_AT} AS last_update_time,
                   COALESCE(l.run_state, :idle) AS run_state
            FROM sessions s
            LEFT JOIN session_run_locks l
                   ON l.app_name = s.app_name AND l.user_id = s.user_id AND l.session_id = s.id
            {_SESSION_FILTERS}
            ORDER BY s.create_time DESC, s.id
            LIMIT :limit OFFSET :offset
            """,
            self._get_filter_params(
                app_name, user_id, search, created_from, created_to, updated_from, updated_to,
                idle=RunState.IDLE, limit=limit, offset=offset
            )
        )

    async def count_sessions(
            self,
            app_name: str,
            user_id: str | None = None,
            search: str | None = None,
            created_from: datetime | None = None,
            created_to: datetime | None = None,
            updated_from: datetime | None = None,
            updated_to: datetime | None = None
    ) -> int:
        row = await self._db.fetch_one(
            f"""
            SELECT count(*) AS total
            FROM sessions s
            {_SESSION_FILTERS}
            """,
            self._get_filter_params(
                app_name, user_id, search, created_from, created_to, updated_from, updated_to
            )
        )
        return row["total"]

    @staticmethod
    def _get_filter_params(
            app_name: str,
            user_id: str | None,
            search: str | None,
            created_from: datetime | None,
            created_to: datetime | None,
            updated_from: datetime | None,
            updated_to: datetime | None,
            **extra
    ) -> dict:
        return {
            "app": app_name,
            "uid": user_id,
            "search": search,
            "created_from": created_from,
            "created_to": created_to,
            "updated_from": updated_from,
            "updated_to": updated_to,
            "title": SessionStateFields.TITLE,
            **extra
        }
