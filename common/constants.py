import pathlib
from enum import StrEnum

ROOT_DIR = pathlib.Path(__file__).parent.parent

HEALTH_CHECK_TIMEOUT = 5


class AppNames(StrEnum):
    ROOT = "data_agent"
    SYSTEM = "system_agent"


class AgentNames(StrEnum):
    ROOT = "root_orchestrator"
    SYSTEM = "system_agent"
    MILVUS = "milvus_scanner"
    MONGODB = "mongodb_scanner"


class EventAuthors(StrEnum):
    USER = "user"
    SYSTEM = "system"


class ArtifactPrefix(StrEnum):
    DATA_URI = "data_uri"
    FILENAME = "filename"
    CONTENT_TYPE = "content_type"


class ModelReasoningEffort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SessionStateFields(StrEnum):
    TITLE = "session_title"
