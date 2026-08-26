import asyncio
import asyncpg
import logging
from typing import Annotated
from fastapi import APIRouter, status, HTTPException, Depends, Request

from common.config import SETTINGS
from common.constants import HEALTHY_STATUS, UNHEALTHY_STATUS, HEALTH_CHECK_TIMEOUT
from data_agent.schemas import CheckHealthResponse
from data_agent.storage import ObjectStorage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def get_object_storage(request: Request) -> ObjectStorage:
    return request.app.state.object_storage


ObjectStorageService = Annotated[ObjectStorage, Depends(get_object_storage)]


async def _ping_db() -> None:
    connection = await asyncpg.connect(
        host=SETTINGS.postgresql_db.host,
        port=SETTINGS.postgresql_db.port,
        database=SETTINGS.postgresql_db.name,
        user="postgres"
    )
    try:
        await connection.execute("SELECT 1")
    finally:
        await connection.close()


async def check_db_status() -> str:
    try:
        await asyncio.wait_for(_ping_db(), timeout=HEALTH_CHECK_TIMEOUT)

        return HEALTHY_STATUS
    except Exception as e:
        logger.exception(f"Database health check failed: {str(e)}")
        return UNHEALTHY_STATUS


async def check_object_storage_status(object_storage: ObjectStorage) -> str:
    try:
        objects = await asyncio.wait_for(
            object_storage.list_paginated_objects(max_items=1),
            timeout=HEALTH_CHECK_TIMEOUT
        )

        return HEALTHY_STATUS if objects is not None else UNHEALTHY_STATUS
    except Exception as e:
        logger.exception(f"Object storage health check failed: {str(e)}")
        return UNHEALTHY_STATUS


@router.get(
    "/health",
    response_model=CheckHealthResponse,
    status_code=status.HTTP_200_OK
)
async def check_health(object_storage: ObjectStorageService):
    try:
        db_status, object_storage_status = await asyncio.gather(
            check_db_status(),
            check_object_storage_status(object_storage)
        )

        logger.info(f"Checked health: db={db_status} object_storage={object_storage_status}")
        return CheckHealthResponse(db_status=db_status, object_storage_status=object_storage_status)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
