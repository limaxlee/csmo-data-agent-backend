"""Application settings — Pydantic Settings loaded from environment / .env file."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg2://defect:defect@localhost:5432/defect"
    debug: bool = False


class ThumbnailSettings(BaseSettings):
    """Worker capacity knobs; safe defaults also fit existing 2 GiB deployments."""
    model_config = SettingsConfigDict(env_prefix="NATIVE_THUMBNAIL_", env_file=".env", extra="ignore")
    workers: int = Field(default=4, ge=1, le=16)
    memory_mib: int = Field(default=1024, ge=1024, le=16384)


class Settings(DatabaseSettings):
    # ── App ──
    app_name: str = "DefectAgent Backend"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8080

    # ── JWT Auth ──
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_minutes: int = 60 * 24 * 7

    # Central web-auth service tokens have their own signing key.
    service_jwt_secret: str | None = None

    @model_validator(mode="after")
    def validate_sso_secret(self) -> Settings:
        if (
            not self.service_jwt_secret
            or not self.service_jwt_secret.strip()
            # Central web-auth owns the shared key, including legacy keys below
            # 32 bytes. Do not impose a separate length policy in this consumer.
            or self.service_jwt_secret == self.secret_key
            or self.secret_key.lower().startswith("change-me")
            or self.service_jwt_secret.lower().startswith("change-me")
        ):
            raise ValueError("SSO requires a separate configured SERVICE_JWT_SECRET")
        return self

    # ── Agent Service ──
    agent_service_base_url: str = "http://localhost:8001"
    # Temporary per-chunk/line diagnostics; payloads are never logged.
    agent_sse_transport_diagnostics: bool = False
    # Maximum number of runs dispatched to the agent at the same time during initial POST /runs.
    max_concurrent_runs: int = Field(default=7, ge=1)
    # Maximum number of concurrent LLM-agent training/generation executions (after plan approval).
    # Requests beyond this limit wait in a FIFO queue and start automatically as slots free up.
    max_concurrent_trainings: int = Field(default=7, ge=1)
    # Observation warning threshold, NOT a training duration or failure deadline.
    run_stall_timeout_seconds: float = Field(default=300.0, gt=0)
    run_confirmation_timeout_seconds: float = Field(default=120.0, gt=0)
    run_sse_heartbeat_seconds: float = Field(default=10, gt=0, le=60)
    # An interrupt waiting on the user may sit quiet for a long time, but not
    # forever: past this age a run whose newest event is still the question is
    # reported as unobserved, never cancelled without Agent evidence.
    run_input_wait_timeout_seconds: float = 86400.0

    # ── Object Storage (MinIO/S3) ──
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "defect-agent"
    minio_secure: bool = False
    minio_verify_ssl: bool = True  # Set False to skip SSL verification (self-signed certs)


    # ── Storage ──
    storage_root: str = "artifacts"
    cache_root: str = ".cache"
    # When False (default), S3 initialisation failure raises instead of
    # silently falling back to the local filesystem.  Set True for local
    # development where S3/MinIO is not available.
    storage_allow_local_fallback: bool = False
    storage_create_bucket: bool = True  # Disable for an existing remote/shared bucket.

    # ── CORS ──
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
