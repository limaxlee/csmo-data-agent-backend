import time
import logging
from fastapi import Request

logger = logging.getLogger(__name__)


async def log_requests_middleware(request: Request, call_next):
    start_time = time.monotonic()
    logger.info(f"Request: {request.method} {request.url.path}?{request.query_params}")

    response = await call_next(request)

    process_time = (time.monotonic() - start_time) * 1000
    logger.info(f"Response: {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}ms)")
    return response
