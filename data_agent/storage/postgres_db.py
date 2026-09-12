import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from common.config import SETTINGS

logger = logging.getLogger(__name__)


class PostgresDBClient:
    def __init__(self, db_name: str = SETTINGS.postgresql_db.name):
        host = SETTINGS.postgresql_db.host
        port = SETTINGS.postgresql_db.port
        connection_uri = f"postgresql+asyncpg://postgres@{host}:{port}/{db_name}"
        self._engine: AsyncEngine = create_async_engine(
            connection_uri,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
        )

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(text(query), params or {})

    async def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> dict | None:
        async with self._engine.begin() as conn:
            result = await conn.execute(text(query), params or {})
            row = result.mappings().first()
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[dict]:
        async with self._engine.begin() as conn:
            result = await conn.execute(text(query), params or {})
            return [dict(row) for row in result.mappings().all()]

    async def close(self):
        await self._engine.dispose()
        logger.info("PostgresDBClient engine disposed")
