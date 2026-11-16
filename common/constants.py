import pathlib
from enum import StrEnum

ROOT_DIR = pathlib.Path(__file__).parent.parent

CONTENT_TYPE = "application/octet-stream"

HEALTH_CHECK_TIMEOUT = 5

DEFAULT_AGENT_RESPONSE = "No response received."

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
