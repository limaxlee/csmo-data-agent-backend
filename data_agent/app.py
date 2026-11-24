from fastapi import FastAPI
from contextlib import asynccontextmanager
from google.adk.sessions import DatabaseSessionService

from data_agent.agents import root_agent
from data_agent.exceptions import register_exception_handlers
from data_agent.infra import (
    ObjectStorage, PostgreSQLClient, ObjectStorageArtifactService,
    SessionLockRepository, SessionRepository, UserRepository, postgresql_dsn
)
from data_agent.middleware import register_middleware
from data_agent.routers import router
from data_agent.services import AgentRunner, TitleGenerator, HealthChecker, TokenVerifier, UserManager
from data_agent.utils import shutdown_logs_executor


@asynccontextmanager
async def lifespan(app: FastAPI):
    object_storage = ObjectStorage()
    await object_storage.connect()

    db_client = PostgreSQLClient()

    session_lock = SessionLockRepository(db_client=db_client)
    await session_lock.initialize()

    user_repository = UserRepository(db_client=db_client)
    await user_repository.initialize()

    # The session service creates its tables on first use. The session repository reads them directly,
    # so they are created here, before the first request can arrive.
    session_service = DatabaseSessionService(db_url=postgresql_dsn())
    await session_service.prepare_tables()

    app.state.object_storage = object_storage
    app.state.health_checker = HealthChecker(db_client=db_client, object_storage=object_storage)
    app.state.token_verifier = TokenVerifier()
    app.state.user_manager = UserManager(user_repository=user_repository)
    app.state.agent_runner = AgentRunner(
        agent=root_agent,
        session_service=session_service,
        artifact_service=ObjectStorageArtifactService(storage=object_storage),
        title_generator=TitleGenerator(),
        session_lock=session_lock,
        session_repository=SessionRepository(db_client=db_client)
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
    register_exception_handlers(app)

    return app


app = create_app()
