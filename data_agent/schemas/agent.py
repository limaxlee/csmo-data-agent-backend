from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field, AwareDatetime

from common.constants import (
    RunState, CONTENT_TYPE, MAX_USER_ID_LENGTH, MAX_SEARCH_LENGTH, DEFAULT_SESSION_LIMIT, MAX_SESSION_LIMIT
)


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


class SessionSummaryInfo(BaseModel):
    user_id: str
    session_id: str
    session_title: str | None = None
    created_at: datetime
    last_update_time: datetime
    run_state: RunState = RunState.IDLE


class ListAllSessionsRequest(BaseModel):
    user_id: str | None = Field(default=None, max_length=MAX_USER_ID_LENGTH)
    search: str | None = Field(default=None, max_length=MAX_SEARCH_LENGTH)
    created_from: AwareDatetime | None = None
    created_to: AwareDatetime | None = None
    updated_from: AwareDatetime | None = None
    updated_to: AwareDatetime | None = None
    limit: int = Field(default=DEFAULT_SESSION_LIMIT, ge=1, le=MAX_SESSION_LIMIT)
    offset: int = Field(default=0, ge=0)


class ListAllSessionsResponse(BaseModel):
    sessions: list[SessionSummaryInfo] = []
    total: int = 0


class CreateSessionResponse(BaseModel):
    session_id: str


class GetSessionResponse(SessionInfo):
    pass


class LoadSessionArtifactRequest(BaseModel):
    filename: str
    data_uri: str
    media_type: str = CONTENT_TYPE


class LoadSessionArtifactResponse(BaseModel):
    content: bytes
    media_type: str


class GetRunStateResponse(BaseModel):
    session_id: str
    run_state: RunState


class RenameSessionRequest(BaseModel):
    session_title: str


class CreateSessionTitleResponse(BaseModel):
    session_title: str


class RunAgentRequest(BaseModel):
    query: str


class RunAgentResponse(BaseModel):
    response: str
    timestamp: datetime
