from datetime import datetime
from pydantic import BaseModel


class RunAgentRequest(BaseModel):
    query: str


class RunAgentResponse(BaseModel):
    response: str
    timestamp: datetime
