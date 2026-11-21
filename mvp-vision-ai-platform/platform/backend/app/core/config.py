"""Application configuration."""

import logging
import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    API_BASE_URL: str = "http://localhost:8000"  # Base URL for callbacks (override in production)
    PROJECT_NAME: str = "Vision AI Training Platform - MVP"
    BACKEND_PORT: int = 8000
    # The queue is durable in every mode. Embedded is the first deployment stage;
    # standalone reuses the exact same registry/runtime in another process.
    TRAINING_DIAGNOSTICS_ENABLED: bool = False
    # API instances must explicitly opt in to consuming shared preparation queues.
    SPLIT_WORKER_ENABLED: bool = False
    TRAINING_DATA_INPUT_WORKER_ENABLED: bool = False
    # Auto-labeling availability is derived from the runner environment wiring
    # (AUTO_LABELING_ENVIRONMENT_JSON); GPU_QUEUE_ENABLED is the ops kill-switch.
    AUTO_LABELING_BATCH_ENABLED: bool = False
    AUTO_LABELING_EXECUTION_MODE: Literal["rq", "backend"] = "rq"
    AUTO_LABELING_SHUTDOWN_GRACE_SECONDS: float = Field(default=10, ge=0, le=120)
    # Operator-controlled runner bundle manifest; no client-selected environments.
    AUTO_LABELING_ENVIRONMENT_JSON: Optional[str] = None
    GPU_QUEUE_ENABLED: bool = False
    GPU_QUEUE_SLOTS_JSON: str = "[]"
    GPU_MANAGED_RUNNERS_JSON: str = "[]"
    GPU_RUNNER_CONTAINERS_JSON: str = "[]"
    GPU_RUNNER_MODE: Literal["container", "persistent"] = "container"
    GPU_RUNNER_API_KEY: Optional[str] = None
    INFERENCE_CACHE_DIR: str = "/var/lib/platform/inference-cache"
    GPU_PREPARATION_LEASE_SECONDS: int = Field(default=1800, ge=60, le=3600)
    GPU_RUNNER_LOCK_DIR: str = "/tmp/platform-managed-runner-locks"
    GPU_RUNNER_HOST_ID_PATH: str = "/etc/machine-id"
    GPU_QUEUE_LEASE_SECONDS: int = Field(default=120, ge=30, le=3600)
    GPU_QUEUE_BATCH_UNITS: int = Field(default=16, ge=1, le=64)
    GPU_QUEUE_POLL_SECONDS: float = Field(default=2, ge=0.1, le=30)
    AGENT_EXECUTION_MODE: str = "embedded"
    AGENT_MAX_CONCURRENCY: int = Field(default=1, ge=1, le=8)
    AGENT_POLL_INTERVAL_SECONDS: float = Field(default=2.0, gt=0, le=60)
    AGENT_SHUTDOWN_GRACE_SECONDS: float = Field(default=5.0, ge=0, le=60)

    # Supply the endpoint through the PROMETHEUS_URL environment variable.
    # Keep it empty by default so deployment-specific addresses are not embedded in source.
    PROMETHEUS_URL: str = ""
    PROMETHEUS_TIMEOUT_SECONDS: float = Field(default=15.0, gt=0, le=60)

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @field_validator("API_V1_PREFIX")
    @classmethod
    def normalize_api_v1_prefix(cls, v: str) -> str:
        """Normalize API prefix so deployments can mount under a subpath."""
        raw = str(v or "/api/v1").strip()
        if not raw.startswith("/"):
            raw = f"/{raw}"
        normalized = raw.rstrip("/")
        return normalized or "/api/v1"

    @field_validator("AGENT_EXECUTION_MODE")
    @classmethod
    def validate_agent_execution_mode(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in {"disabled", "embedded", "standalone"}:
            raise ValueError("AGENT_EXECUTION_MODE must be disabled, embedded or standalone")
        return normalized

    @property
    def BACKEND_CORS_ORIGINS(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Frontend URL (for email links, redirects, etc.)
    FRONTEND_URL: str = "http://localhost:3000"

    # Database (set via DATABASE_URL environment variable)
    # If not set, will use local SQLite in __init__
    DATABASE_URL: Optional[str] = None

    # Runtime mode. Cluster is the default to preserve existing deployments.
    # Offline mode is selected explicitly by the desktop/launcher bootstrap.
    DICE_RUNTIME_MODE: str = "cluster"
    DICE_WORKSPACE_ROOT: Optional[str] = None
    DICE_OFFLINE_DB_PATH: Optional[str] = None
    DICE_OFFLINE_STORAGE_ROOT: Optional[str] = None
    DICE_OFFLINE_TRAINING_MODE: str = "subprocess"
    DICE_OFFLINE_TRAINER_PYTHON: Optional[str] = None
    DICE_OFFLINE_APP_HOST: str = "127.0.0.1"
    DICE_OFFLINE_APP_PORT: Optional[int] = None
    DICE_OFFLINE_PLATFORM_API_PORT: Optional[int] = None
    # Static frontend bundle (Next.js `output: 'export'` out/ directory).
    # When set (or present at the offline default location), the backend
    # serves the UI itself so no separate web server is needed on-target.
    DICE_FRONTEND_DIST: Optional[str] = None

    # Shared User Database (Phase 11: Microservice Separation)
    # Shared between Platform and Labeler for user authentication
    # If not set, will use separate SQLite in __init__
    USER_DATABASE_URL: Optional[str] = None

    # Activation Database (Dashboard Activation tab)
    # Separate from Platform DB / Shared User DB
    ACTIVATION_DATABASE_URL: Optional[str] = None

    # Redis (Phase 5: Multi-backend state management)
    # If not set, will default to localhost in main.py
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    DATASET_CACHE_DISCOVERY_ENABLED: bool = False
    DATASET_CACHE_DISCOVERY_INTERVAL_SECONDS: int = Field(default=300, ge=5, le=3600)
    # Redis holds pending publish warmups; use one shared cache writer by default.
    DATASET_CACHE_MAX_ACTIVE_JOBS: int = Field(default=1, ge=1, le=32)
    # Separate durable instance recommended; shared cache eviction would lose logs.
    ACTIVITY_REDIS_URL: Optional[str] = None
    ACTIVITY_STREAM_MAX_BYTES: int = Field(default=16 * 1024 * 1024, ge=4 * 1024 * 1024)
    ACTIVITY_STREAM_ARCHIVE_BYTES: int = Field(default=1024 * 1024, ge=65536)
    ACTIVITY_STREAM_RECEIPT_SECONDS: int = Field(default=7 * 86400, ge=600)
    # Zero retains archives; operators set the existing bucket lifecycle separately.
    ACTIVITY_ARCHIVE_RETENTION_DAYS: int = Field(default=0, ge=0)

    # LLM Configuration (Dual Provider Support)
    # Provider: "openai" or "gemini"
    LLM_PROVIDER: str = "openai"  # Options: "openai", "gemini"
    LLM_MODEL: str = "gpt-4o-mini"  # OpenAI: gpt-4o-mini, Gemini: gemini-2.0-flash-exp
    LLM_TEMPERATURE: float = 0.0

    # OpenAI Compatible API (when LLM_PROVIDER=openai)
    # Supports: OpenAI, Azure OpenAI, LocalAI, Ollama, vLLM, etc.
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"  # Override for custom endpoints

    # Google Gemini API (when LLM_PROVIDER=gemini)
    GOOGLE_API_KEY: str = ""

    # Dashboard Agent uses an OpenAI-compatible endpoint and the read-only
    # Dashboard MCP service. Keep these separate from the general chatbot LLM.
    DASHBOARD_AGENT_LLM_BASE_URL: str = ""
    DASHBOARD_AGENT_LLM_API_KEY: str = ""
    DASHBOARD_AGENT_LLM_MODEL: str = ""
    DASHBOARD_AGENT_LLM_TIMEOUT_SECONDS: float = Field(default=60.0, gt=0, le=600)
    DASHBOARD_AGENT_MCP_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0, le=600)
    DASHBOARD_AGENT_MAX_TOOL_CALL_ROUNDS: int = Field(default=5, ge=1, le=20)
    DASHBOARD_AGENT_MAX_TOKENS: int = Field(default=2048, ge=1, le=32768)
    DASHBOARD_MCP_URL: str = ""

    # 레거시 인증은 ADFS 전환으로 제거됨 (인증=web-auth service JWT / PAT,
    # 사용자 디렉토리=공유 users 테이블).

    # Security & Authentication (Legacy - kept for service JWT)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Service-to-Service Authentication (Phase 11.5.6: Hybrid JWT)
    # Shared secret for inter-service JWTs
    # Generated with: openssl rand -hex 32
    SERVICE_JWT_SECRET: str = "service-jwt-secret-change-in-production-use-openssl-rand-hex-32"
    # Bounded tolerance for clock skew between internal service nodes.
    SERVICE_JWT_LEEWAY_SECONDS: int = Field(default=5, ge=0, le=30)

    # Runner/legacy-trainer release distribution (manifest + presigned S3 URLs)
    # now lives in web-auth (app/runner-releases, app/runner-envs,
    # app/legacy-trainer-releases) — it needs no DB/training-platform state,
    # just a role check off the service JWT's roles claim.

    # ========================================
    # Chatbot Integration (Learning Progress API)
    # ========================================
    # Shared secret for chatbot auth bypass. Generate with: openssl rand -hex 32
    CHATBOT_API_KEY: str = ""
    CHATBOT_DEFAULT_RECENT_JOBS: int = 10
    CHATBOT_MAX_RECENT_JOBS: int = 50

    # Storage Paths (will be converted to absolute paths)
    # Note: Paths are relative to project root (mvp-vision-ai-platform/)
    UPLOAD_DIR: str = "./data/uploads"
    OUTPUT_DIR: str = "./data/outputs"
    MODEL_DIR: str = "./data/models"
    LOG_DIR: str = "./data/logs"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Convert relative paths to absolute paths based on platform directory
        # __file__ = platform/backend/app/core/config.py
        # parent x3 = platform/backend -> platform/
        project_root = Path(__file__).parent.parent.parent.absolute()

        for attr in ["UPLOAD_DIR", "OUTPUT_DIR", "MODEL_DIR", "LOG_DIR"]:
            path_value = getattr(self, attr)
            if not os.path.isabs(path_value):
                # Convert relative path to absolute
                abs_path = project_root / path_value.lstrip("./")
                setattr(self, attr, str(abs_path))

        self.DICE_RUNTIME_MODE = str(self.DICE_RUNTIME_MODE or "cluster").strip().lower()
        if self.DICE_RUNTIME_MODE not in {"cluster", "offline"}:
            raise ValueError("DICE_RUNTIME_MODE must be one of: cluster, offline")

        workspace_root: Path | None = None
        if self.DICE_RUNTIME_MODE == "offline":
            if not self.DICE_WORKSPACE_ROOT:
                raise ValueError("DICE_WORKSPACE_ROOT is required when DICE_RUNTIME_MODE=offline")
            workspace_root = Path(self.DICE_WORKSPACE_ROOT).expanduser().resolve()
            self.DICE_WORKSPACE_ROOT = str(workspace_root)

            if not self.DICE_OFFLINE_DB_PATH:
                self.DICE_OFFLINE_DB_PATH = str(workspace_root / "db" / "dice.sqlite")
            if not self.DICE_OFFLINE_STORAGE_ROOT:
                self.DICE_OFFLINE_STORAGE_ROOT = str(workspace_root / "storage")

            offline_paths = {
                "DICE_OFFLINE_DB_PATH": Path(self.DICE_OFFLINE_DB_PATH).expanduser().resolve(),
                "DICE_OFFLINE_STORAGE_ROOT": Path(self.DICE_OFFLINE_STORAGE_ROOT)
                .expanduser()
                .resolve(),
            }
            for name, path in offline_paths.items():
                if not path.is_relative_to(workspace_root):
                    raise ValueError(f"{name} must be inside DICE_WORKSPACE_ROOT")
                setattr(self, name, str(path))

            if str(self.DICE_OFFLINE_TRAINING_MODE or "").strip().lower() != "subprocess":
                raise ValueError("Offline trainer runtime currently supports only subprocess mode")

            if not self.DICE_FRONTEND_DIST:
                default_dist = workspace_root / "frontend" / "out"
                if (default_dist / "index.html").is_file():
                    self.DICE_FRONTEND_DIST = str(default_dist)

            if not self.DATABASE_URL:
                self.DATABASE_URL = f"sqlite:///{self.DICE_OFFLINE_DB_PATH}"
            if not self.USER_DATABASE_URL:
                self.USER_DATABASE_URL = self.DATABASE_URL

        # Handle DATABASE_URL
        if not self.DATABASE_URL:
            # No DATABASE_URL set - use local SQLite
            db_path = project_root / "data" / "db" / "vision_platform.db"
            self.DATABASE_URL = f"sqlite:///{db_path}"
            logger.info("[CONFIG] Using local SQLite database: %s", db_path)
        elif self.DATABASE_URL.startswith("sqlite:///./"):
            # Relative SQLite path - convert to absolute
            rel_path = self.DATABASE_URL.replace("sqlite:///./", "")
            abs_path = project_root / rel_path
            self.DATABASE_URL = f"sqlite:///{abs_path}"
            logger.info("[CONFIG] Using SQLite database: %s", abs_path)
        elif "postgresql" in self.DATABASE_URL or "postgres" in self.DATABASE_URL:
            # PostgreSQL URL from Railway - use as-is
            # Mask password for logging
            masked_url = self._mask_database_url(self.DATABASE_URL)
            logger.info("[CONFIG] Using PostgreSQL database: %s", masked_url)
        else:
            # Unknown database URL format
            logger.info("[CONFIG] Using database URL: %s", self.DATABASE_URL)

        # Handle USER_DATABASE_URL (Phase 11: Shared User DB)
        if not self.USER_DATABASE_URL:
            # No USER_DATABASE_URL set - use local SQLite (Tier 1)
            # Windows: C:\temp\shared_users.db
            # Linux/Mac: /tmp/shared_users.db
            import platform

            if platform.system() == "Windows":
                user_db_path = Path("C:/temp/shared_users.db")
            else:
                user_db_path = Path("/tmp/shared_users.db")

            self.USER_DATABASE_URL = f"sqlite:///{user_db_path}"
            logger.info("[CONFIG] Using shared SQLite User DB (Tier 1): %s", user_db_path)
        elif self.USER_DATABASE_URL.startswith("sqlite:///./"):
            # Relative SQLite path - convert to absolute
            rel_path = self.USER_DATABASE_URL.replace("sqlite:///./", "")
            abs_path = project_root / rel_path
            self.USER_DATABASE_URL = f"sqlite:///{abs_path}"
            logger.info("[CONFIG] Using shared SQLite User DB: %s", abs_path)
        elif "postgresql" in self.USER_DATABASE_URL or "postgres" in self.USER_DATABASE_URL:
            # PostgreSQL URL (Tier 2: Railway or Tier 3: K8s)
            masked_url = self._mask_database_url(self.USER_DATABASE_URL)
            logger.info("[CONFIG] Using shared PostgreSQL User DB: %s", masked_url)
        else:
            logger.info("[CONFIG] Using shared User DB URL: %s", self.USER_DATABASE_URL)

        # Handle ACTIVATION_DATABASE_URL
        if not self.ACTIVATION_DATABASE_URL:
            logger.warning("[CONFIG] ACTIVATION_DATABASE_URL is not configured")
        elif self.ACTIVATION_DATABASE_URL.startswith("sqlite:///./"):
            rel_path = self.ACTIVATION_DATABASE_URL.replace("sqlite:///./", "")
            abs_path = project_root / rel_path
            self.ACTIVATION_DATABASE_URL = f"sqlite:///{abs_path}"
            logger.info("[CONFIG] Using Activation SQLite DB: %s", abs_path)
        elif (
            "postgresql" in self.ACTIVATION_DATABASE_URL
            or "postgres" in self.ACTIVATION_DATABASE_URL
        ):
            masked_url = self._mask_database_url(self.ACTIVATION_DATABASE_URL)
            logger.info("[CONFIG] Using Activation PostgreSQL DB: %s", masked_url)
        else:
            logger.info("[CONFIG] Using Activation DB URL: %s", self.ACTIVATION_DATABASE_URL)

    @staticmethod
    def _mask_database_url(url: str) -> str:
        """Mask the password in a database URL for safe logging.

        Args:
            url: Database URL (e.g., postgresql://user:pass@host:5432/db)

        Returns:
            Masked URL (e.g., postgresql://user:***@host:5432/db),
            or the original URL when it contains no credentials.
        """
        if "@" not in url:
            return url
        creds, host = url.split("@", maxsplit=1)
        username = creds.split(":")[0]
        return f"{username}:***@{host}"

    @property
    def is_offline_runtime(self) -> bool:
        """Return True when the backend is running in offline workstation mode."""
        return self.DICE_RUNTIME_MODE == "offline"

    # Labeler Service (Phase 11.5: Dataset Service Integration)
    # Labeler Backend is the Single Source of Truth for dataset metadata
    # Platform queries Labeler API for dataset information
    LABELER_API_URL: str = "http://localhost:8011"

    # User Service owns Group-based access control (Phase 2) — Trainer calls
    # its internal API to resolve project WORKER/OWNER access instead of
    # querying the local project_members table.
    # Includes the API prefix; callers append API-relative paths only.
    USER_SERVICE_API_URL: str = "http://localhost:8003/user/api/v1"

    # Bot Backend (Chat-based Learning Management)
    # Platform sends training completion notifications to Bot Backend
    # Bot Backend forwards to Teams/Slack based on user preferences
    # Format: scheme + host + /api/v1/dice-bot (notification endpoint appended automatically)
    BOT_BACKEND_URL: str = "http://localhost:9000/api/v1/dice-bot"

    # Training Defaults
    DEFAULT_BATCH_SIZE: int = 32
    DEFAULT_EPOCHS: int = 50
    DEFAULT_LEARNING_RATE: float = 0.001

    # Training Execution Mode (Phase 12: TrainingManager)
    # - "subprocess": Direct subprocess execution (Tier 0, local development)
    # - "kubernetes": K8s Job execution via KubernetesTrainingManager (Tier 1+, production)
    # - "space": K8s adapter Job that launches GPU training through Space CLI
    TRAINING_MODE: str = "subprocess"
    # Enable only after deploying recording-aware backend replicas and SDK images.

    # PaddleOCR TorchServe (Image Tools OCR) - legacy per-model GPU pods.
    # Same-namespace K8s service DNS; use {pod} placeholder.
    # Kept as fallback for models not yet migrated to DICE Runner (see below).
    PADDLEOCR_SERVICE_BASE_URL: str = "http://{pod}"
    PADDLEOCR_INFERENCE_TIMEOUT_SECONDS: int = 3600
    # Optional per-pod base URLs for local/cluster-external debugging (not committed).
    # When K8s DNS http://{pod} is unreachable, client retries with these bases.
    PADDLEOCR_V5_EN: Optional[str] = None
    PADDLEOCR_V5_KR: Optional[str] = None
    # Env keys use dots (PADDLEOCR_VL_v1.6); Python fields use underscores.
    PADDLEOCR_VL_v1_6: Optional[str] = Field(default=None, validation_alias="PADDLEOCR_VL_v1.6")

    # DICE Runner (shared GPU inference server; replaces one-pod-per-model TorchServe).
    # Same-namespace K8s service DNS: dice-platform-runner in the `dice` namespace.
    # base_path=/runner is applied by the runner itself, not just the external ingress.
    DICE_RUNNER_BASE_URL: str = "http://dice-platform-runner:8080/runner/api"
    # Optional override base URL for local/cluster-external debugging (not committed).
    DICE_RUNNER_DEBUG_BASE_URL: Optional[str] = None

    class Config:
        # Load .env file for local development
        # Environment variables (e.g., Railway) take precedence over .env file
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()

