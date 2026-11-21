from fastapi import APIRouter

from .auth import router as auth_router
from .logs import router as logs_router
from .admin import router as admin_router
from .agent import router as agent_router
from .health import router as health_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(logs_router)
router.include_router(admin_router)
router.include_router(agent_router)
router.include_router(health_router)
