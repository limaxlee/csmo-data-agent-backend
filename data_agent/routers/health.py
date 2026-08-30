import logging
from fastapi import APIRouter, status, HTTPException

from data_agent.schemas import CheckHealthStatusResponse
from data_agent.utils import check_postgres_health, check_storage_health

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=CheckHealthStatusResponse,
    status_code=status.HTTP_200_OK
)
async def check_health():
    try:
        health_status = CheckHealthStatusResponse(
            server_status="healthy",
            postgresql_db_status="healthy" if await check_postgres_health() else "unhealthy",
            object_storage_status="healthy" if await check_storage_health() else "unhealthy"
        )

        logger.info(f"Checked health status: {health_status}")
        return health_status
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    