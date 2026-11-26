import logging
from typing import Any
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine

from common.config import SETTINGS

logger = logging.getLogger(__name__)


def postgresql_dsn(db_name: str | None = None) -> str:
    db = SETTINGS.postgresql_db
    url = URL.create(
        drivername="postgresql+asyncpg",
        username=db.user,
        password=db.password or None,
        host=db.host,
        port=db.port,
        database=db_name or db.name
    )

    # The password is written into the address with its special characters escaped. Never log this value.
    return url.render_as_string(hide_password=False)


class PostgreSQLClient:
    def __init__(self, db_name: str | None = None):
        self._engine = create_async_engine(
            postgresql_dsn(db_name),
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True
        )

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> None:
        async with self._engine.begin() as connection:
            await connection.execute(text(query), params or {})

    async def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> dict | None:
        async with self._engine.begin() as connection:
            result = await connection.execute(text(query), params or {})
            row = result.mappings().first()
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[dict]:
        async with self._engine.begin() as connection:
            result = await connection.execute(text(query), params or {})
            return [dict(row) for row in result.mappings().all()]

    async def close(self):
        await self._engine.dispose()
        logger.info("PostgreSQL client engine disposed")
