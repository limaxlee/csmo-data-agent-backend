"""FastAPI application factory — creates and configures the app.

This is the entry point: `src.container.app:app`
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.container.settings import get_settings
from src.auth.presentation.controllers import auth_router
from src.common.presentation.controllers import system_router
from src.plan.presentation.controllers import plan_router
from src.result.presentation.controllers import result_router, thread_result_router
from src.run.presentation.controllers import run_router
from src.thread.presentation.controllers import thread_router
from src.train_data.presentation.controllers import train_data_router
from src.train_data.application.errors import IntegrationError
from src.common.presentation.exception_handlers import register_exception_handlers

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    from src.container.consumers import resume_consumers, shutdown_consumers
    from src.container.migrations import warn_if_migrations_pending
    from src.container.infrastructure import init_storage

    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # The schema belongs to Alembic now — see alembic/README and the project
    # README for `alembic upgrade head`. Creating tables here would let the app
    # silently run against a schema no migration ever produced, which is how the
    # live database drifted from the entity definitions in the first place.
    warn_if_migrations_pending()

    # Build the shared StorageManager once at startup so its head_bucket
    # round trip happens here, not on every request.
    init_storage()

    # Re-attach event consumers to runs a previous process left non-terminal
    await resume_consumers()

    try:
        yield
    finally:
        await shutdown_consumers()
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Backend API server for DefectAgent — manages users, conversations, "
            "training data, and relays agent execution events."
        ),
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers (domain exceptions → HTTP responses)
    register_exception_handlers(app)

    # Register routers
    app.include_router(system_router)
    app.include_router(auth_router)
    app.include_router(thread_router)
    app.include_router(run_router)
    app.include_router(train_data_router)
    from src.train_data.presentation.native_router import router as native_train_data_router
    app.include_router(native_train_data_router)
    from src.train_data.presentation.native_task_router import router as native_task_router
    app.include_router(native_task_router)

    @app.exception_handler(IntegrationError)
    async def integration_error(request, exc: IntegrationError):
        return JSONResponse(status_code=exc.status, content={"error": {
            "code": exc.code, "retryable": exc.status in {429, 502, 504},
        }})
    app.include_router(plan_router)
    app.include_router(result_router)
    app.include_router(thread_result_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.container.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
