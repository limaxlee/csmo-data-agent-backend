import asyncio
import logging

from common.constants import HEALTH_CHECK_TIMEOUT
from data_agent.infra import ObjectStorage, PostgresClient

logger = logging.getLogger(__name__)


class HealthChecker:
    """Liveness checks against the process-wide clients created at startup.

    Each check reuses the pooled connection of the injected client and is
    bounded by `timeout_seconds`, so a hung backend reports as unhealthy
    instead of stalling the request.
    """

    def __init__(
            self,
            db_client: PostgresClient,
            object_storage: ObjectStorage,
            timeout_seconds: float = HEALTH_CHECK_TIMEOUT
    ):
        self._db = db_client
        self._storage = object_storage
        self._timeout_seconds = timeout_seconds

    async def check_postgres(self) -> bool:
        try:
            row = await asyncio.wait_for(self._db.fetch_one("SELECT 1 AS ping"), self._timeout_seconds)
            return bool(row) and row.get("ping") == 1
        except Exception as e:
            logger.warning(f"Postgres health check failed: {type(e).__name__}: {str(e)}")
            return False

    async def check_storage(self) -> bool:
        try:
            await asyncio.wait_for(
                self._storage.client.head_bucket(Bucket=self._storage.bucket),
                self._timeout_seconds
            )
            return True
        except Exception as e:
            logger.warning(f"Object storage health check failed: {type(e).__name__}: {str(e)}")
            return False
