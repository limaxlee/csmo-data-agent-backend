import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from common.config import SETTINGS
from data_agent.routers import router
from data_agent.utils import initialize_logger, shutdown_logs_executor
from data_agent.dependencies import get_agent_runner, get_db_session_service, get_object_storage

@asynccontextmanager
async def lifespan(app: FastAPI):
    object_storage = get_object_storage()
    await object_storage.connect()

    get_db_session_service()
    get_agent_runner()
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

if __name__ == "__main__":
    logger = initialize_logger("cosmo_data_agent.log")
    logger.info("Starting COSMO Data Agent Backend")

    uvicorn.run(app, host="0.0.0.0", port=SETTINGS.server_port, log_config=None)
