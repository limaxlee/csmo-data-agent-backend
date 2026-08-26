from fastapi import APIRouter

from .health import router as health_router
from .logs import router as logs_router
from .runner import router as runner_router
from .session import router as session_router

router = APIRouter()
router.include_router(health_router)
router.include_router(logs_router)
router.include_router(session_router)
router.include_router(runner_router)
