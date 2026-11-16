import asyncio
import logging

from common.constants import HEALTH_CHECK_TIMEOUT
from data_agent.infra import ObjectStorage, PostgreSQLClient

logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(
            self,
            db_client: PostgreSQLClient,
            object_storage: ObjectStorage,
            timeout_seconds: float = HEALTH_CHECK_TIMEOUT
    ):
        self._db = db_client
        self._storage = object_storage
        self._timeout_seconds = timeout_seconds

    async def check_postgresql(self) -> bool:
        try:
            row = await asyncio.wait_for(self._db.fetch_one("SELECT 1 AS ping"), self._timeout_seconds)
            return bool(row) and row.get("ping") == 1
        except Exception as e:
            logger.warning(f"Postgres health check failed: {str(e)}")
            return False

    async def check_object_storage(self) -> bool:
        try:
            return await asyncio.wait_for(self._storage.head_bucket(), self._timeout_seconds)
        except Exception as e:
            logger.warning(f"Object storage health check failed: {str(e)}")
            return False
