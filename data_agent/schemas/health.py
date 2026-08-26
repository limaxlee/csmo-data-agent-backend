from pydantic import BaseModel


class CheckHealthResponse(BaseModel):
    server_status: str = "healthy"
    db_status: str
    object_storage_status: str
