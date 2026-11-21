import pytest
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from data_agent import app as app_module
from data_agent.app import create_app, lifespan
from data_agent.exceptions import AuthError, handle_auth_error
from data_agent.middleware.logging import log_requests


class TestCreateApp:
    def test_create_app(self):
        app = create_app()

        assert app.title == "DICE Data Agent Backend"

        paths = set(app.openapi()["paths"])
        assert {
            "/health", "/logs", "/apps/users/{user_id}/sessions", "/auth/me", "/admin/users",
            "/admin/users/{user_id}", "/admin/users/{user_id}/access-log", "/admin/admins",
            "/admin/admins/{user_id}"
        } <= paths

        middleware_classes = [middleware.cls for middleware in app.user_middleware]
        assert CORSMiddleware in middleware_classes
        assert any(
            middleware.cls is BaseHTTPMiddleware and middleware.kwargs["dispatch"] is log_requests
            for middleware in app.user_middleware
        )

        assert app.exception_handlers[AuthError] is handle_auth_error

    def test_create_app_uses_lifespan(self, mocker):
        entered = []

        @asynccontextmanager
        async def _lifespan(app):
            entered.append("start")
            yield
            entered.append("stop")

        mocker.patch.object(app_module, "lifespan", _lifespan)

        with TestClient(create_app()):
            assert entered == ["start"]
        assert entered == ["start", "stop"]

    def test_module_app(self):
        assert isinstance(app_module.app, FastAPI)


class TestLifespan:
    @pytest.fixture
    def infra(self, mocker):
        object_storage = mocker.MagicMock()
        object_storage.connect = mocker.AsyncMock(return_value=object_storage)
        object_storage.close = mocker.AsyncMock()
        mocker.patch.object(app_module, "ObjectStorage", return_value=object_storage)

        db_client = mocker.MagicMock()
        db_client.close = mocker.AsyncMock()
        mocker.patch.object(app_module, "PostgreSQLClient", return_value=db_client)

        session_lock = mocker.MagicMock()
        session_lock.initialize = mocker.AsyncMock()
        session_lock_cls = mocker.patch.object(app_module, "SessionLockRepository", return_value=session_lock)

        user_repository = mocker.MagicMock()
        user_repository.initialize = mocker.AsyncMock()
        user_repository_cls = mocker.patch.object(app_module, "UserRepository", return_value=user_repository)

        return mocker.MagicMock(
            object_storage=object_storage,
            db_client=db_client,
            session_lock=session_lock,
            session_lock_cls=session_lock_cls,
            user_repository=user_repository,
            user_repository_cls=user_repository_cls,
            health_checker_cls=mocker.patch.object(app_module, "HealthChecker"),
            token_verifier_cls=mocker.patch.object(app_module, "TokenVerifier"),
            user_manager_cls=mocker.patch.object(app_module, "UserManager"),
            agent_runner_cls=mocker.patch.object(app_module, "AgentRunner"),
            session_service_cls=mocker.patch.object(app_module, "DatabaseSessionService"),
            artifact_service_cls=mocker.patch.object(app_module, "ObjectStorageArtifactService"),
            title_generator_cls=mocker.patch.object(app_module, "TitleGenerator"),
            postgresql_dsn=mocker.patch.object(app_module, "postgresql_dsn", return_value="postgresql+asyncpg://dsn"),
            shutdown_logs_executor=mocker.patch.object(app_module, "shutdown_logs_executor")
        )

    @pytest.mark.asyncio
    async def test_lifespan(self, infra):
        app = FastAPI()

        async with lifespan(app):
            infra.object_storage.connect.assert_awaited_once()
            infra.session_lock_cls.assert_called_once_with(db_client=infra.db_client)
            infra.session_lock.initialize.assert_awaited_once()
            infra.user_repository_cls.assert_called_once_with(db_client=infra.db_client)
            infra.user_repository.initialize.assert_awaited_once()

            assert app.state.object_storage is infra.object_storage
            assert app.state.health_checker is infra.health_checker_cls.return_value
            assert app.state.token_verifier is infra.token_verifier_cls.return_value
            assert app.state.user_manager is infra.user_manager_cls.return_value
            assert app.state.agent_runner is infra.agent_runner_cls.return_value

            infra.health_checker_cls.assert_called_once_with(
                db_client=infra.db_client,
                object_storage=infra.object_storage
            )
            infra.token_verifier_cls.assert_called_once_with()
            infra.user_manager_cls.assert_called_once_with(user_repository=infra.user_repository)
            infra.session_service_cls.assert_called_once_with(db_url="postgresql+asyncpg://dsn")
            infra.artifact_service_cls.assert_called_once_with(storage=infra.object_storage)
            infra.title_generator_cls.assert_called_once_with()

            kwargs = infra.agent_runner_cls.call_args.kwargs
            assert kwargs["agent"] is app_module.root_agent
            assert kwargs["session_service"] is infra.session_service_cls.return_value
            assert kwargs["artifact_service"] is infra.artifact_service_cls.return_value
            assert kwargs["title_generator"] is infra.title_generator_cls.return_value
            assert kwargs["session_lock"] is infra.session_lock

            infra.db_client.close.assert_not_awaited()
            infra.object_storage.close.assert_not_awaited()
            infra.shutdown_logs_executor.assert_not_called()

        infra.db_client.close.assert_awaited_once()
        infra.object_storage.close.assert_awaited_once()
        infra.shutdown_logs_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_closes_clients_when_app_fails(self, infra):
        app = FastAPI()

        with pytest.raises(RuntimeError, match="boom"):
            async with lifespan(app):
                raise RuntimeError("boom")

        infra.db_client.close.assert_awaited_once()
        infra.object_storage.close.assert_awaited_once()
        infra.shutdown_logs_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_fails_when_storage_connection_fails(self, mocker, infra):
        infra.object_storage.connect = mocker.AsyncMock(side_effect=RuntimeError("storage down"))
        app = FastAPI()

        with pytest.raises(RuntimeError, match="storage down"):
            async with lifespan(app):
                pass

        infra.session_lock.initialize.assert_not_awaited()
        infra.user_repository.initialize.assert_not_awaited()
        infra.agent_runner_cls.assert_not_called()
        infra.db_client.close.assert_not_awaited()
