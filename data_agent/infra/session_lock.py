import logging

from common.constants import RunState
from data_agent.infra.postgres_client import PostgresClient

logger = logging.getLogger(__name__)


class SessionLockRepository:
    """Per-session run lock backed by a Postgres row.

    There is no lease: a lock is held until the run releases it. A crashed
    process therefore leaves its locks in the RUNNING state. When
    `reset_on_startup` is true, `initialize` marks every such lock idle, which
    is only safe when this is the sole backend process: with several workers
    or replicas a restarting instance would wipe locks held by running ones.
    """

    def __init__(self, db_client: PostgresClient, reset_on_startup: bool = True):
        self._db = db_client
        self._reset_on_startup = reset_on_startup

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
        # Tables created by the previous lease-based version still carry this column.
        await self._db.execute("ALTER TABLE session_run_locks DROP COLUMN IF EXISTS lease_expires_at")
        if self._reset_on_startup:
            await self.reset_all()
        else:
            logger.warning("Session run locks were not reset at startup; locks of crashed runs stay held")
        logger.info("Session lock table ready")

    async def reset_all(self):
        """Mark every lock idle. Only safe when no run can be in progress, i.e. at startup."""
        await self._db.execute(
            """
            UPDATE session_run_locks
            SET run_state = :idle, updated_at = now()
            WHERE run_state = :running
            """,
            {"idle": RunState.IDLE, "running": RunState.RUNNING},
        )
        logger.info("Reset all session run locks to idle")

    async def try_acquire(self, app_name: str, user_id: str, session_id: str) -> bool:
        # Single atomic upsert: Postgres row-locks the conflicting row, so a
        # concurrent acquire waits, re-checks the WHERE against the committed
        # row, and gets no row back if the session is already running.
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
            self._params(app_name, user_id, session_id)
        )

        acquired = row is not None
        if acquired:
            logger.info(f"Acquired run lock for session {session_id} of user {user_id}")
        else:
            logger.info(f"Session {session_id} of user {user_id} is already running")

        return acquired

    async def release(self, app_name: str, user_id: str, session_id: str) -> bool:
        """Mark the lock idle. Never raises: a failed release must not mask the
        outcome of the run that held it. If it fails the lock stays held until
        the next startup reset."""
        try:
            await self._db.execute(
                """
                UPDATE session_run_locks
                SET run_state = :idle, updated_at = now()
                WHERE app_name = :app AND user_id = :uid AND session_id = :sid
                """,
                self._params(app_name, user_id, session_id),
            )
        except Exception as e:
            logger.exception(f"Failed to release run lock for session {session_id} of user {user_id}: {str(e)}")
            return False

        logger.info(f"Released run lock for session {session_id} of user {user_id}")
        return True

    async def get_run_state(self, app_name: str, user_id: str, session_id: str) -> RunState:
        row = await self._db.fetch_one(
            """
            SELECT run_state
            FROM session_run_locks
            WHERE app_name = :app AND user_id = :uid AND session_id = :sid
            """,
            self._params(app_name, user_id, session_id),
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
