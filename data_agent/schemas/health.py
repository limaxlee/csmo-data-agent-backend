from pydantic import BaseModel


class CheckHealthStatusResponse(BaseModel):
    server_status: str = "healthy"
    postgresql_db_status: str
    object_storage_status: str
