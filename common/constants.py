import pathlib
from enum import StrEnum

ROOT_DIR = pathlib.Path(__file__).parent.parent

CONTENT_TYPE = "application/octet-stream"

HEALTH_CHECK_TIMEOUT = 5

DEFAULT_AGENT_RESPONSE = "No response received."

BEARER_PREFIX = "Bearer "
SERVICE_TOKEN_TYPE = "service"
SERVICE_TOKEN_ALGORITHM = "HS256"

MAX_USER_ID_LENGTH = 255
MAX_FULL_NAME_LENGTH = 255
MAX_USER_AGENT_LENGTH = 512

DEFAULT_ACCESS_LOG_LIMIT = 100
MAX_ACCESS_LOG_LIMIT = 1000

class ModelReasoningEffort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentNames(StrEnum):
    ROOT = "root_orchestrator"
    TITLE = "title_agent"
    MILVUS = "milvus_scanner"
    MONGODB = "mongodb_scanner"


class AppNames(StrEnum):
    ROOT = "data_agent"
    TITLE = "title_generator"


class RunState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"


class EventAuthors(StrEnum):
    USER = "user"
    SYSTEM = "system"


class SessionStateFields(StrEnum):
    TITLE = "session_title"


class ArtifactPrefix(StrEnum):
    DATA_URI = "data_uri"
    FILENAME = "filename"
    CONTENT_TYPE = "content_type"


class AuthErrorCode(StrEnum):
    INVALID_TOKEN = "invalid_token"
    ACCOUNT_INACTIVE = "account_inactive"
    USER_MISMATCH = "user_mismatch"
    ADMIN_REQUIRED = "admin_required"
    USER_NOT_FOUND = "user_not_found"
    ADMIN_NOT_FOUND = "admin_not_found"
    LAST_ADMIN = "last_admin"
