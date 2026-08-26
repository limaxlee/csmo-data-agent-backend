import asyncio

from fastapi import FastAPI

from data_agent.__main__ import app, lifespan


class TestApp:
    def test_lifespan(self, mocker):
        object_storage = mocker.MagicMock()
        object_storage.connect = mocker.AsyncMock()
        object_storage.close = mocker.AsyncMock()
        agent_runner = mocker.MagicMock()

        mocker.patch("data_agent.__main__.ObjectStorage", return_value=object_storage)
        mocker.patch("data_agent.__main__.RootAgentRunner", return_value=agent_runner)
        artifact_service = mocker.patch("data_agent.__main__.OSArtifactService")
        system_runner = mocker.patch("data_agent.__main__.SystemAgentRunner")
        shutdown_logs = mocker.patch("data_agent.__main__.shutdown_logs_executor")

        test_app = FastAPI()

        async def _exercise():
            async with lifespan(test_app):
                object_storage.connect.assert_awaited_once()
                assert test_app.state.object_storage is object_storage
                assert test_app.state.agent_runner is agent_runner
                # Still open while the app is serving.
                object_storage.close.assert_not_awaited()

        asyncio.run(_exercise())

        artifact_service.assert_called_once_with(storage=object_storage)
        system_runner.assert_called_once()
        object_storage.close.assert_awaited_once()
        shutdown_logs.assert_called_once()

    def test_app(self):
        paths = set(app.router.routes[index].path for index in range(len(app.router.routes)))

        assert "/health" in paths
        assert "/logs" in paths
        assert "/apps/users/{user_id}/sessions" in paths
        assert "/apps/users/{user_id}/sessions/{session_id}/run" in paths
