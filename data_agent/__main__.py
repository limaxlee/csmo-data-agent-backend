import uvicorn

from common.config import SETTINGS
from data_agent.app import app
from data_agent.utils import initialize_logger

if __name__ == "__main__":
    logger = initialize_logger("cosmo_data_agent.log")
    logger.info("Starting DICE Data Agent Backend")

    uvicorn.run(app, host="0.0.0.0", port=SETTINGS.server_port, log_config=None)
