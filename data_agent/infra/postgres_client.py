import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from common.config import SETTINGS

logger = logging.getLogger(__name__)


def postgres_dsn(db_name: str | None = None) -> str:
    """SQLAlchemy asyncpg DSN for the configured Postgres server. Single source for every engine in the process."""
    db = SETTINGS.postgresql_db
    return f"postgresql+asyncpg://{db.user}@{db.host}:{db.port}/{db_name or db.name}"


class PostgresClient:
    def __init__(self, db_name: str | None = None):
        self._engine: AsyncEngine = create_async_engine(
            postgres_dsn(db_name),
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
        logger.info("PostgresClient engine disposed")
