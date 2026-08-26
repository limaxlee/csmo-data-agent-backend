from functools import lru_cache
from google.adk.sessions import BaseSessionService

from data_agent.services import (
    RootAgentRunner, PostgreSQLSessionService, OSArtifactService, SystemAgentRunner,
    create_session_store
)
from data_agent.storage import ObjectStorage


@lru_cache
def get_object_storage() -> ObjectStorage:
    return ObjectStorage()


@lru_cache
def get_session_store() -> BaseSessionService:
    return create_session_store()


@lru_cache
def get_db_session_service() -> PostgreSQLSessionService:
    return PostgreSQLSessionService(
        session_service=get_session_store(),
        system_runner=SystemAgentRunner(),
        # object_storage=get_object_storage()
    )


@lru_cache
def get_agent_runner() -> RootAgentRunner:
    return RootAgentRunner(
        session_service=get_session_store(),
        artifact_service=OSArtifactService(storage=get_object_storage()),
        db_session_service=get_db_session_service()
    )
