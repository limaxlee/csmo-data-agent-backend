import logging

from common.constants import RunState
from data_agent.infra.postgresql_client import PostgreSQLClient

logger = logging.getLogger(__name__)


class SessionLockRepository:
    def __init__(self, db_client: PostgreSQLClient):
        self._db = db_client

    async def initialize(self):
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS session_run_locks (
                app_name   TEXT NOT NULL,
                user_id    TEXT NOT NULL,
                session_id TEXT NOT NULL,
                run_state  TEXT NOT NULL DEFAULT 'idle',
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (app_name, user_id, session_id)
            )
        """)
        await self._db.execute("ALTER TABLE session_run_locks DROP COLUMN IF EXISTS lease_expires_at")
        await self._db.execute(
            """
            UPDATE session_run_locks
            SET run_state = :idle, updated_at = now()
            WHERE run_state = :running
            """,
            {"idle": RunState.IDLE, "running": RunState.RUNNING}
        )

        logger.info(f"Session run locks were reset to {RunState.IDLE} state: session table is ready")

    async def acquire(self, app_name: str, user_id: str, session_id: str) -> bool:
        row = await self._db.fetch_one(
            """
            INSERT INTO session_run_locks (app_name, user_id, session_id, run_state)
            VALUES (:app, :uid, :sid, :running)
            ON CONFLICT (app_name, user_id, session_id) DO UPDATE
                SET run_state = :running,
                    updated_at = now()
                WHERE session_run_locks.run_state = :idle
            RETURNING session_id
            """,
            self._get_params(app_name, user_id, session_id)
        )

        acquired = row is not None
        if acquired:
            logger.info(f"Acquired run lock for session {session_id} of user {user_id}")
        else:
            logger.info(f"Session {session_id} of user {user_id} is already running")

        return acquired

    async def release(self, app_name: str, user_id: str, session_id: str) -> bool:
        try:
            await self._db.execute(
                """
                UPDATE session_run_locks
                SET run_state = :idle, updated_at = now()
                WHERE app_name = :app AND user_id = :uid AND session_id = :sid
                """,
                self._get_params(app_name, user_id, session_id)
            )

            logger.info(f"Released run lock for session {session_id} of user {user_id}")
            return True
        except Exception as e:
            logger.exception(f"Failed to release run lock for session {session_id} of user {user_id}: {str(e)}")
            return False

    async def get_run_state(self, app_name: str, user_id: str, session_id: str) -> RunState:
        row = await self._db.fetch_one(
            """
            SELECT run_state
            FROM session_run_locks
            WHERE app_name = :app AND user_id = :uid AND session_id = :sid
            """,
            self._get_params(app_name, user_id, session_id)
        )
        if row and row["run_state"] == RunState.RUNNING:
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
              AND run_state = :running
            """,
            {
                "app": app_name,
                "uid": user_id,
                "sids": session_ids,
                "running": RunState.RUNNING
            },
        )

        running = {row["session_id"] for row in rows}
        return {item: RunState.RUNNING if item in running else RunState.IDLE for item in session_ids}

    async def delete(self, app_name: str, user_id: str, session_id: str):
        await self._db.execute(
            """
            DELETE FROM session_run_locks
            WHERE app_name = :app AND user_id = :uid AND session_id = :sid
            """,
            self._get_params(app_name, user_id, session_id)
        )
        logger.info(f"Deleted run lock for session {session_id} of user {user_id}")

    def _get_params(self, app_name: str, user_id: str, session_id: str, **extra) -> dict:
        return {
            "app": app_name,
            "uid": user_id,
            "sid": session_id,
            "idle": RunState.IDLE,
            "running": RunState.RUNNING,
            **extra
        }
