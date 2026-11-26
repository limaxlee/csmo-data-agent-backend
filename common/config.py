import os
import yaml
import argparse
from typing import Any
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings

from common.constants import ROOT_DIR

_ENV_MAP = {
    "SERVER_PORT": ("server_port", int),
    "MONGODB_MCP_HOST": ("mongodb_mcp.host", str),
    "MONGODB_MCP_PORT": ("mongodb_mcp.port", int),
    "MILVUS_MCP_HOST": ("milvus_mcp.host", str),
    "MILVUS_MCP_PORT": ("milvus_mcp.port", int),
    "POSTGRESQL_DB_HOST": ("postgresql_db.host", str),
    "POSTGRESQL_DB_PORT": ("postgresql_db.port", int),
    "POSTGRESQL_DB_NAME": ("postgresql_db.name", str),
    "POSTGRESQL_DB_USER": ("postgresql_db.user", str),
    "POSTGRESQL_DB_PASSWORD": ("postgresql_db.password", str),
    "OBJECT_STORAGE_BUCKET": ("object_storage.bucket", str),
    "OBJECT_STORAGE_ENDPOINT": ("object_storage.endpoint", str),
    "OBJECT_STORAGE_ACCESS_KEY": ("object_storage.access_key", str),
    "OBJECT_STORAGE_SECRET_KEY": ("object_storage.secret_key", str),
    "ROOT_MODEL_OPENAPI_MODEL": ("root_model_openapi.model", str),
    "ROOT_MODEL_OPENAPI_ENDPOINT": ("root_model_openapi.endpoint", str),
    "ROOT_MODEL_OPENAPI_CLIENT_KEY": ("root_model_openapi.client_key", str),
    "ROOT_MODEL_OPENAPI_PASS_KEY": ("root_model_openapi.pass_key", str),
    "ROOT_MODEL_OPENAPI_MODEL_ID": ("root_model_openapi.model_id", int),
    "TITLE_MODEL_OPENAPI_MODEL": ("title_model_openapi.model", str),
    "TITLE_MODEL_OPENAPI_ENDPOINT": ("title_model_openapi.endpoint", str),
    "TITLE_MODEL_OPENAPI_CLIENT_KEY": ("title_model_openapi.client_key", str),
    "TITLE_MODEL_OPENAPI_PASS_KEY": ("title_model_openapi.pass_key", str),
    "TITLE_MODEL_OPENAPI_MODEL_ID": ("title_model_openapi.model_id", int),
    "AUTH_SERVICE_JWT_SECRET": ("auth.service_jwt_secret", str),
    "AUTH_SERVICE_JWT_ISSUER": ("auth.service_jwt_issuer", str),
    "AUTH_SERVICE_JWT_AUDIENCE": ("auth.service_jwt_audience", str),
}


def _set_nested_config(config: dict[str, Any], key: str, value: Any) -> None:
    *groups, values = key.split(".")
    node = config
    for group in groups:
        node = node.setdefault(group, {})
        if not isinstance(node, dict):
            raise ValueError(f"Config key {group} is invalid: {type(node).__name__}")

    node[values] = value


def load_config() -> dict[str, Any]:
    default_config = os.path.join(ROOT_DIR, "config.yaml")
    parser = argparse.ArgumentParser(description="Data Agent Backend Configurations")
    parser.add_argument("--config", "-c", type=str, help="Path to the config.yaml", default=default_config)
    args, _ = parser.parse_known_args()

    config = {}
    if os.path.isfile(args.config):
        with open(args.config, "r") as f:
            file_config = yaml.safe_load(f) or {}

        if not isinstance(file_config, dict):
            raise ValueError(f"Config file is invalid: {args.config}")

        config.update(file_config)

    for env_name, (key, caster) in _ENV_MAP.items():
        env_value = os.getenv(env_name)
        if env_value is None:
            continue

        try:
            value = caster(env_value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid value for {env_name}: {env_value!r}") from error

        _set_nested_config(config, key, value)

    return config


class MCPConfig(BaseModel):
    host: str
    port: int


class SessionDBConfig(BaseModel):
    host: str
    port: int
    name: str
    user: str
    password: str = ""


class ObjectStorageConfig(BaseModel):
    bucket: str
    endpoint: str
    access_key: str
    secret_key: str


class ModelOpenAPI(BaseModel):
    model: str
    endpoint: str
    client_key: str
    pass_key: str
    model_id: int


class AuthConfig(BaseModel):
    service_jwt_secret: str
    service_jwt_issuer: str = "web-auth"
    service_jwt_audience: str = "dice-backend"

    @field_validator("service_jwt_secret")
    @classmethod
    def validate_service_jwt_secret(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Service JWT secret is empty: set auth.service_jwt_secret or AUTH_SERVICE_JWT_SECRET")

        return value


class Settings(BaseSettings, extra="allow"):
    server_port: int
    cors_origins: list[str] = []

    mongodb_mcp: MCPConfig
    milvus_mcp: MCPConfig

    postgresql_db: SessionDBConfig
    object_storage: ObjectStorageConfig
    root_model_openapi: ModelOpenAPI
    title_model_openapi: ModelOpenAPI

    auth: AuthConfig


SETTINGS = Settings(**load_config())
