import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from common.config import SETTINGS
from data_agent.routers import router, log_requests_middleware
from data_agent.runners import RootAgentRunner, SystemAgentRunner
from data_agent.storage import ObjectStorage, OSArtifactService
from data_agent.utils import initialize_logger, shutdown_logs_executor

@asynccontextmanager
async def lifespan(app: FastAPI):
    object_storage = ObjectStorage()
    await object_storage.connect()

    app.state.object_storage = object_storage
    app.state.agent_runner = RootAgentRunner(
        artifact_service=OSArtifactService(storage=object_storage),
        system_runner=SystemAgentRunner()
    )
    try:
        yield
    finally:
        await object_storage.close()
        shutdown_logs_executor()


app = FastAPI(title="COSMO Data Agent Backend", lifespan=lifespan)
app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(log_requests_middleware)

if __name__ == "__main__":
    logger = initialize_logger("cosmo_data_agent.log")
    logger.info("Starting COSMO Data Agent Backend")

    uvicorn.run(app, host="0.0.0.0", port=SETTINGS.server_port, log_config=None)
