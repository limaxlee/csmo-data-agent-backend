import pathlib

ROOT_DIR = pathlib.Path(__file__).parent.parent

ROOT_APP_NAME = "data_agent"
USER_AUTHOR = "user"

SYSTEM_APP_NAME = "system_agent"
SYSTEM_AUTHOR = "system"

SESSION_TITLE_KEY = "session_title"

PRESIGNED_URL_EXPIRED_IN = 7200
VIEW_DATA_PREFIX = "[View data]"
DATA_URI_PREFIX = "[Actual data url of the uploaded file]"
FILENAME_PREFIX = "[Filename of the uploaded file]"
CONTENT_TYPE = "[Content type of the uploaded file]"

MILVUS_IMAGE_SEARCH_TOOL = "mcp_milvus_extract_embeddings_and_vector_search"

HEALTHY_STATUS = "healthy"
UNHEALTHY_STATUS = "unhealthy"
HEALTH_CHECK_TIMEOUT = 5
