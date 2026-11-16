from fastapi import APIRouter

from .logs import router as logs_router
from .agent import router as agent_router
from .health import router as health_router

router = APIRouter()
router.include_router(logs_router)
router.include_router(agent_router)
router.include_router(health_router)
