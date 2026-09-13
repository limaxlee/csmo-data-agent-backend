import pytest
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from common.config import SETTINGS
from data_agent import app as app_module
from data_agent.app import create_app, lifespan
from data_agent.middleware.logging import log_requests_middleware


class TestCreateApp:
    def test_create_app(self):
        app = create_app()

        assert app.title == "DICE Data Agent Backend"

        paths = set(app.openapi()["paths"])
        assert {"/health", "/logs", "/apps/users/{user_id}/sessions"} <= paths

        middleware_classes = [middleware.cls for middleware in app.user_middleware]
        assert CORSMiddleware in middleware_classes
        assert any(
            middleware.cls is BaseHTTPMiddleware and middleware.kwargs["dispatch"] is log_requests_middleware
            for middleware in app.user_middleware
        )

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
        mocker.patch.object(app_module, "PostgresClient", return_value=db_client)

        lock_repository = mocker.MagicMock()
        lock_repository.initialize = mocker.AsyncMock()
        lock_repository_cls = mocker.patch.object(app_module, "SessionLockRepository", return_value=lock_repository)

        return mocker.MagicMock(
            object_storage=object_storage,
            db_client=db_client,
            lock_repository=lock_repository,
            lock_repository_cls=lock_repository_cls,
            health_checker_cls=mocker.patch.object(app_module, "HealthChecker"),
            agent_runner_cls=mocker.patch.object(app_module, "AgentRunner"),
            session_service_cls=mocker.patch.object(app_module, "DatabaseSessionService"),
            artifact_service_cls=mocker.patch.object(app_module, "ObjectStorageArtifactService"),
            title_generator_cls=mocker.patch.object(app_module, "TitleGenerator"),
            postgres_dsn=mocker.patch.object(app_module, "postgres_dsn", return_value="postgresql+asyncpg://dsn"),
            shutdown_logs_executor=mocker.patch.object(app_module, "shutdown_logs_executor")
        )

    @pytest.mark.asyncio
    async def test_lifespan(self, infra):
        app = FastAPI()

        async with lifespan(app):
            infra.object_storage.connect.assert_awaited_once()
            infra.lock_repository_cls.assert_called_once_with(
                db_client=infra.db_client,
                reset_on_startup=SETTINGS.reset_session_locks
            )
            infra.lock_repository.initialize.assert_awaited_once()

            assert app.state.object_storage is infra.object_storage
            assert app.state.health_checker is infra.health_checker_cls.return_value
            assert app.state.agent_runner is infra.agent_runner_cls.return_value

            infra.health_checker_cls.assert_called_once_with(
                db_client=infra.db_client,
                object_storage=infra.object_storage
            )
            infra.session_service_cls.assert_called_once_with(db_url="postgresql+asyncpg://dsn")
            infra.artifact_service_cls.assert_called_once_with(storage=infra.object_storage)
            infra.title_generator_cls.assert_called_once_with()

            kwargs = infra.agent_runner_cls.call_args.kwargs
            assert kwargs["agent"] is app_module.root_agent
            assert kwargs["session_service"] is infra.session_service_cls.return_value
            assert kwargs["artifact_service"] is infra.artifact_service_cls.return_value
            assert kwargs["title_generator"] is infra.title_generator_cls.return_value
            assert kwargs["lock_repository"] is infra.lock_repository

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

        infra.lock_repository.initialize.assert_not_awaited()
        infra.agent_runner_cls.assert_not_called()
        infra.db_client.close.assert_not_awaited()
