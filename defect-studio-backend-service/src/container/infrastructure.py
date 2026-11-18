"""Shared infrastructure providers — cross-context singletons and shared repo adapters.

These providers are used by multiple Bounded Contexts and therefore live in the
composition root rather than in any single context.

Architecture:
    DB Session → Repository Impl → Adapter (port impl) → Handler (use case impl)
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.auth.application.ports.out.gateways import PasswordEncoder, TokenProvider
from src.common.application.ports.out.gateways import StorageGateway
from src.run.application.ports.out.gateways import AgentGateway
from src.run.domain.services import EventProcessor
from src.run.infrastructure.adapters.gateways.agent_service_adapter import AgentServiceAdapter
from src.auth.infrastructure.adapters.gateways.password_hasher_adapter import PasswordHasherAdapter
from src.common.infrastructure.adapters.gateways.storage_adapter import StorageAdapter
from src.thread.infrastructure.adapters.repositories.message_repository_adapter import MessageRepositoryAdapter
from src.thread.infrastructure.adapters.repositories.thread_repository_adapter import ThreadRepositoryAdapter
from src.auth.infrastructure.adapters.gateways.token_service_adapter import TokenServiceAdapter
from src.container.database.engine import get_db
from src.container.external.agent_http_client import AgentHttpClient
from src.container.external.storage_manager import StorageManager
from src.thread.infrastructure.repositories.message_repository_impl import MessageRepositoryImpl
from src.thread.infrastructure.repositories.thread_repository_impl import ThreadRepositoryImpl


# ──────────────────────────────────────────────────────────────
# Override hooks (for testing)
# ──────────────────────────────────────────────────────────────

_agent_service_override: AgentGateway | None = None

_storage: StorageGateway | None = None


def set_agent_service_override(agent: AgentGateway | None) -> None:
    """Set a mock agent service (used by test fixtures)."""
    global _agent_service_override
    _agent_service_override = agent


# ──────────────────────────────────────────────────────────────
# Infrastructure singletons
# ──────────────────────────────────────────────────────────────

_event_processor = EventProcessor()


def get_event_processor() -> EventProcessor:
    return _event_processor


def get_token_service() -> TokenProvider:
    return TokenServiceAdapter()


def get_password_hasher() -> PasswordEncoder:
    return PasswordHasherAdapter()


def get_agent_service() -> AgentGateway:
    if _agent_service_override is not None:
        return _agent_service_override
    from src.container.settings import get_settings

    settings = get_settings()
    client = AgentHttpClient(base_url=settings.agent_service_base_url)
    return AgentServiceAdapter(client)


def _build_storage() -> StorageGateway:
    from src.container.settings import get_settings

    settings = get_settings()
    manager = StorageManager(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
        secure=settings.minio_secure,
    )
    return StorageAdapter(manager)


def init_storage() -> None:
    """Build the shared StorageManager at startup.

    Called from the FastAPI lifespan handler so the head_bucket
    round trip happens once, before any request is served.
    """
    global _storage
    _storage = _build_storage()


def reset_storage() -> None:
    """Clear the shared storage singleton (for tests)."""
    global _storage
    _storage = None


def get_storage() -> StorageGateway:
    global _storage
    if _storage is None:
        _storage = _build_storage()
    return _storage


# ──────────────────────────────────────────────────────────────
# Cross-context Repository Adapters (Shared Kernel)
# ──────────────────────────────────────────────────────────────
# ThreadRepository and MessageRepository are shared across multiple
# contexts (run, plan, result, train_data, thread itself), so their
# providers live here rather than in a single context.

def get_thread_repo_adapter(db: Session = Depends(get_db)) -> ThreadRepositoryAdapter:
    return ThreadRepositoryAdapter(ThreadRepositoryImpl(db))


def get_message_repo_adapter(db: Session = Depends(get_db)) -> MessageRepositoryAdapter:
    return MessageRepositoryAdapter(MessageRepositoryImpl(db))

