from typing import Any
from datetime import datetime
from pydantic import BaseModel

from common.constants import RunState, CONTENT_TYPE


class SessionInfo(BaseModel):
    session_id: str
    app_name: str
    user_id: str
    state: dict[str, Any] = {}
    events: list[Any] = []
    last_update_time: datetime
    run_state: RunState = RunState.IDLE


class ListSessionsResponse(BaseModel):
    sessions: list[SessionInfo] = []


class CreateSessionResponse(BaseModel):
    session_id: str


class RenameSessionRequest(BaseModel):
    session_title: str


class CreateSessionTitleResponse(BaseModel):
    session_title: str


class LoadSessionArtifactRequest(BaseModel):
    filename: str
    data_uri: str
    media_type: str = CONTENT_TYPE


class LoadSessionArtifactResponse(BaseModel):
    content: bytes
    media_type: str


class RunAgentRequest(BaseModel):
    query: str
    new_session: bool = False


class RunAgentResponse(BaseModel):
    response: str
    timestamp: datetime


class GetRunStateResponse(BaseModel):
    session_id: str
    run_state: RunState
