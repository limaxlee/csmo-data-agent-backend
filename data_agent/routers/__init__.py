import time
import logging
from fastapi import APIRouter, Request

from .health import router as health_router
from .logs import router as logs_router
from .runner import router as runner_router

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(health_router)
router.include_router(logs_router)
router.include_router(runner_router)


async def log_requests_middleware(request: Request, call_next):
    start_time = time.monotonic()
    logger.info(f"Request: {request.method} {request.url.path}?{request.query_params}")

    response = await call_next(request)

    process_time = (time.monotonic() - start_time) * 1000
    logger.info(f"Response: {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}ms)")
    return response
