from typing import Any
from datetime import datetime
from pydantic import BaseModel


class SessionInfo(BaseModel):
    session_id: str
    app_name: str
    user_id: str
    state: dict[str, Any] = {}
    events: list[Any] = []
    last_update_time: datetime


class ListSessionsResponse(BaseModel):
    sessions: list[SessionInfo] = []


class CreateSessionResponse(BaseModel):
    session_id: str


class RenameSessionRequest(BaseModel):
    session_title: str


class CreateSessionTitleResponse(BaseModel):
    session_title: str


class LoadSessionArtifactRequest(BaseModel):
    data_uri: str


class LoadSessionArtifactResponse(BaseModel):
    content: bytes
    media_type: str


class RunAgentRequest(BaseModel):
    query: str
    new_session: bool = False


class RunAgentResponse(BaseModel):
    response: str
    timestamp: datetime
