import logging
from contextlib import asynccontextmanager
from enum import StrEnum

from data_agent.storage.postgres_db import PostgresDBClient

logger = logging.getLogger(__name__)

DEFAULT_LEASE_SECONDS = 3000


class RunState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"


class SessionBusyError(Exception):
    pass


class SessionLockService:
    def __init__(self, db_client: PostgresDBClient, lease_seconds: int = DEFAULT_LEASE_SECONDS):
        self._db = db_client
        self._lease_seconds = lease_seconds

    async def initialize(self):
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS session_run_locks (
                app_name         TEXT NOT NULL,
                user_id          TEXT NOT NULL,
                session_id       TEXT NOT NULL,
                run_state        TEXT NOT NULL DEFAULT 'idle',
                lease_expires_at TIMESTAMPTZ,
                updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (app_name, user_id, session_id)
            )
        """)
        logger.info("Session lock table ready")

    @asynccontextmanager
    async def hold(self, app_name: str, user_id: str, session_id: str):
        if not await self.try_acquire(app_name, user_id, session_id):
            raise SessionBusyError(f"Session {session_id} already has a run in progress")
        try:
            yield
        finally:
            await self.release(app_name, user_id, session_id)

    async def try_acquire(self, app_name: str, user_id: str, session_id: str) -> bool:
        row = await self._db.fetch_one(
            """
            INSERT INTO session_run_locks (app_name, user_id, session_id, run_state, lease_expires_at)
            VALUES (:app, :uid, :sid, :running, now() + make_interval(secs => :lease))
            ON CONFLICT (app_name, user_id, session_id) DO UPDATE
                SET run_state = :running,
                    lease_expires_at = now() + make_interval(secs => :lease),
                    updated_at = now()
                WHERE session_run_locks.run_state = :idle
                   OR session_run_locks.lease_expires_at < now()
            RETURNING session_id
            """,
            self._params(app_name, user_id, session_id, lease=self._lease_seconds)
        )

        acquired = row is not None
        if acquired:
            logger.info(f"Acquired run lock for session {session_id} of user {user_id}")
        else:
            logger.info(f"Session {session_id} of user {user_id} is already running")

        return acquired

    async def release(self, app_name: str, user_id: str, session_id: str):
        await self._db.execute(
            """
            UPDATE session_run_locks
            SET run_state = :idle, lease_expires_at = NULL, updated_at = now()
            WHERE app_name = :app AND user_id = :uid AND session_id = :sid
            """,
            self._params(app_name, user_id, session_id),
        )
        logger.info(f"Released run lock for session {session_id} of user {user_id}")

    async def get_run_state(self, app_name: str, user_id: str, session_id: str) -> RunState:
        row = await self._db.fetch_one(
            """
            SELECT run_state, lease_expires_at > now() AS lease_valid
            FROM session_run_locks
            WHERE app_name = :app AND user_id = :uid AND session_id = :sid
            """,
            self._params(app_name, user_id, session_id),
        )
        if row and row["run_state"] == RunState.RUNNING and row["lease_valid"]:
            return RunState.RUNNING
        return RunState.IDLE

    async def get_run_states(
            self,
            app_name: str,
            user_id: str,
            session_ids: list[str],
    ) -> dict[str, RunState]:
        if not session_ids:
            return {}

        rows = await self._db.fetch_all(
            """
            SELECT session_id
            FROM session_run_locks
            WHERE app_name = :app AND user_id = :uid AND session_id = ANY(:sids)
              AND run_state = :running AND lease_expires_at > now()
            """,
            {
                "app": app_name,
                "uid": user_id,
                "sids": session_ids,
                "running": RunState.RUNNING
            },
        )

        running = {row["session_id"] for row in rows}
        return {sid: RunState.RUNNING if sid in running else RunState.IDLE for sid in session_ids}

    async def delete(self, app_name: str, user_id: str, session_id: str):
        await self._db.execute(
            """
            DELETE FROM session_run_locks
            WHERE app_name = :app AND user_id = :uid AND session_id = :sid
            """,
            self._params(app_name, user_id, session_id),
        )
        logger.info(f"Deleted run lock for session {session_id} of user {user_id}")

    def _params(self, app_name: str, user_id: str, session_id: str, **extra) -> dict:
        return {
            "app": app_name,
            "uid": user_id,
            "sid": session_id,
            "idle": RunState.IDLE,
            "running": RunState.RUNNING,
            **extra
        }
