import logging
from typing import Annotated
from fastapi import APIRouter, status, HTTPException, Depends, Request

from data_agent.schemas import CheckHealthStatusResponse
from data_agent.services import HealthChecker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def get_health_checker(request: Request) -> HealthChecker:
    return request.app.state.health_checker


HealthCheckerDep = Annotated[HealthChecker, Depends(get_health_checker)]


@router.get(
    "/health",
    response_model=CheckHealthStatusResponse,
    status_code=status.HTTP_200_OK
)
async def check_health(checker: HealthCheckerDep):
    try:
        health_status = CheckHealthStatusResponse(
            server_status="healthy",
            postgresql_db_status="healthy" if await checker.check_postgres() else "unhealthy",
            object_storage_status="healthy" if await checker.check_storage() else "unhealthy"
        )

        logger.info(f"Checked health status: {health_status}")
        return health_status
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
