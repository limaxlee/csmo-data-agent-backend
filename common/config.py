import os
import yaml
import argparse
from typing import Any
from pydantic import BaseModel
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
    "OBJECT_STORAGE_BUCKET": ("object_storage.bucket", str),
    "OBJECT_STORAGE_ENDPOINT": ("object_storage.endpoint", str),
    "OBJECT_STORAGE_ACCESS_KEY": ("object_storage.access_key", str),
    "OBJECT_STORAGE_SECRET_KEY": ("object_storage.secret_key", str),
    "MODEL_OPENAPI_ENDPOINT": ("model_openapi.endpoint", str),
    "MODEL_OPENAPI_CLIENT_KEY": ("model_openapi.client_key", str),
    "MODEL_OPENAPI_PASS_KEY": ("model_openapi.pass_key", str),
    "MODEL_OPENAPI_ROOT_MODEL_ID": ("model_openapi.root_model_id", int),
    "MODEL_OPENAPI_SYSTEM_MODEL_ID": ("model_openapi.system_model_id", int)
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


class ObjectStorageConfig(BaseModel):
    bucket: str
    endpoint: str
    access_key: str
    secret_key: str


class ModelOpenAPI(BaseModel):
    endpoint: str
    client_key: str
    pass_key: str
    root_model_id: int
    system_model_id: int


class Settings(BaseSettings, extra="allow"):
    server_port: int

    mongodb_mcp: MCPConfig
    milvus_mcp: MCPConfig

    postgresql_db: SessionDBConfig
    object_storage: ObjectStorageConfig
    model_openapi: ModelOpenAPI


SETTINGS = Settings(**load_config())
