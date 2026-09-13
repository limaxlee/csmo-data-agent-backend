from fastapi import FastAPI
from contextlib import asynccontextmanager
from google.adk.sessions import DatabaseSessionService

from common.config import SETTINGS
from data_agent.agents import root_agent
from data_agent.routers import router
from data_agent.middleware import register_middleware
from data_agent.services import AgentRunner, TitleGenerator, HealthChecker
from data_agent.infra import (
    ObjectStorage, ObjectStorageArtifactService, PostgresClient, SessionLockRepository, postgres_dsn
)
from data_agent.utils import shutdown_logs_executor


@asynccontextmanager
async def lifespan(app: FastAPI):
    object_storage = ObjectStorage()
    await object_storage.connect()

    # One engine (connection pool) per process — created here and only here.
    db_client = PostgresClient()
    lock_repository = SessionLockRepository(db_client=db_client, reset_on_startup=SETTINGS.reset_session_locks)
    await lock_repository.initialize()

    app.state.object_storage = object_storage
    app.state.health_checker = HealthChecker(db_client=db_client, object_storage=object_storage)
    app.state.agent_runner = AgentRunner(
        agent=root_agent,
        session_service=DatabaseSessionService(db_url=postgres_dsn()),
        artifact_service=ObjectStorageArtifactService(storage=object_storage),
        title_generator=TitleGenerator(),
        lock_repository=lock_repository
    )
    try:
        yield
    finally:
        await db_client.close()
        await object_storage.close()
        shutdown_logs_executor()


def create_app() -> FastAPI:
    app = FastAPI(title="DICE Data Agent Backend", lifespan=lifespan)
    app.include_router(router)
    register_middleware(app)
    return app


app = create_app()
