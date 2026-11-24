import pytest
from datetime import datetime, timezone
from fastapi import UploadFile

from common.constants import RunState
from data_agent.schemas import (
    LoadSessionArtifactRequest, RenameSessionRequest, RunAgentRequest, ListAllSessionsRequest
)
from data_agent.services.agent_runner import AgentRunner

_NOW = datetime(2026, 11, 24, 10, 15, tzinfo=timezone.utc)


def _build_event(mocker, author, texts):
    event = mocker.MagicMock()
    event.author = author
    if texts is None:
        event.content = None
    else:
        event.content = mocker.MagicMock()
        event.content.parts = [mocker.MagicMock(text=text) for text in texts]
    return event


class TestAgentRunner:
    @pytest.fixture
    def agent_runner(self, mocker):
        mocker.patch("data_agent.services.agent_runner.Runner", return_value=mocker.MagicMock())

        session_service = mocker.MagicMock()
        session_service.get_session = mocker.AsyncMock(return_value=None)
        session_service.append_event = mocker.AsyncMock()

        session_lock = mocker.MagicMock()

        return AgentRunner(
            agent=mocker.MagicMock(),
            session_service=session_service,
            artifact_service=mocker.MagicMock(),
            title_generator=mocker.MagicMock(),
            session_lock=session_lock,
            session_repository=mocker.MagicMock()
        )

    @pytest.mark.asyncio
    async def test_create_session(self, mocker, agent_runner):
        agent_runner._session_service.create_session = mocker.AsyncMock(return_value=mocker.MagicMock(id="session-1"))

        result = await agent_runner.create_session(user_id="user-1")

        assert result.session_id == "session-1"
        generated_id = (agent_runner._session_service.create_session.await_args.kwargs["session_id"])
        assert len(generated_id) == 32
        assert agent_runner._session_service.create_session.await_args.kwargs["user_id"] == "user-1"

        agent_runner._session_service.create_session = mocker.AsyncMock(side_effect=Exception("Runtime error"))

        with pytest.raises(Exception):
            await agent_runner.create_session(user_id="user-1")

    @pytest.mark.asyncio
    async def test_list_sessions(self, mocker, agent_runner):
        session = mocker.MagicMock(
            id="session-1",
            app_name="data_agent",
            user_id="user-1",
            state={"session_title": "Greetings"},
            events=[],
            last_update_time=1700000000.0
        )
        agent_runner._session_service.list_sessions = mocker.AsyncMock(
            return_value=mocker.MagicMock(sessions=[session])
        )
        agent_runner._session_lock.get_run_states = mocker.AsyncMock(return_value={'session-1': RunState.RUNNING})

        result = await agent_runner.list_sessions(user_id='user-1')
        assert len(result.sessions) == 1
        assert result.sessions[0].session_id == 'session-1'
        assert result.sessions[0].last_update_time.timestamp() == 1700000000.0
        assert agent_runner._session_lock.get_run_states.await_args.kwargs['session_ids'] == ['session-1']

        agent_runner._session_service.list_sessions = mocker.AsyncMock(side_effect=Exception('Runtime error'))
        with pytest.raises(Exception):
            await agent_runner.list_sessions(user_id='user-1')

    @pytest.mark.asyncio
    async def test_list_all_sessions(self, mocker, agent_runner):
        session_repository = agent_runner._session_repository

        session_repository.list_sessions = mocker.AsyncMock(return_value=[
            {
                "user_id": "user-1",
                "session_id": "session-1",
                "session_title": "Greetings",
                "created_at": _NOW,
                "last_update_time": _NOW,
                "run_state": "running"
            },
            {
                "user_id": "user-2",
                "session_id": "session-2",
                "session_title": None,
                "created_at": _NOW,
                "last_update_time": _NOW,
                "run_state": "idle"
            }
        ])
        session_repository.count_sessions = mocker.AsyncMock(return_value=30)

        result = await agent_runner.list_all_sessions(ListAllSessionsRequest())

        assert [session.session_id for session in result.sessions] == ["session-1", "session-2"]
        assert result.sessions[0].user_id == "user-1"
        assert result.sessions[0].session_title == "Greetings"
        assert result.sessions[0].created_at == _NOW
        assert result.sessions[0].run_state == RunState.RUNNING
        assert result.sessions[1].session_title is None
        assert result.sessions[1].run_state == RunState.IDLE
        assert result.total == 30

        filters = {
            "user_id": None,
            "search": None,
            "created_from": None,
            "created_to": None,
            "updated_from": None,
            "updated_to": None
        }

        session_repository.list_sessions.assert_awaited_once_with(
            app_name=agent_runner._app_name,
            **filters,
            limit=50,
            offset=0
        )
        session_repository.count_sessions.assert_awaited_once_with(app_name=agent_runner._app_name, **filters)

        session_repository.list_sessions = mocker.AsyncMock(return_value=[])
        session_repository.count_sessions = mocker.AsyncMock(return_value=0)

        result = await agent_runner.list_all_sessions(ListAllSessionsRequest(
            user_id=" User-1 ",
            search=" Greetings ",
            created_from=_NOW,
            created_to=_NOW,
            updated_from=_NOW,
            updated_to=_NOW,
            limit=10,
            offset=20
        ))

        assert result.sessions == []
        assert result.total == 0

        filters = {
            "user_id": "User-1",
            "search": "Greetings",
            "created_from": _NOW,
            "created_to": _NOW,
            "updated_from": _NOW,
            "updated_to": _NOW
        }

        session_repository.list_sessions.assert_awaited_once_with(
            app_name=agent_runner._app_name,
            **filters,
            limit=10,
            offset=20
        )
        session_repository.count_sessions.assert_awaited_once_with(app_name=agent_runner._app_name, **filters)

        # An empty filter is no filter: it must not be searched for as an empty login ID.
        await agent_runner.list_all_sessions(ListAllSessionsRequest(user_id="", search="   "))

        assert session_repository.list_sessions.await_args.kwargs["user_id"] is None
        assert session_repository.list_sessions.await_args.kwargs["search"] is None

        session_repository.list_sessions = mocker.AsyncMock(side_effect=Exception("Runtime error"))

        with pytest.raises(Exception, match="Runtime error"):
            await agent_runner.list_all_sessions(ListAllSessionsRequest())

    @pytest.mark.asyncio
    async def test_delete_session(self, mocker, agent_runner):
        artifact_service = agent_runner._artifact_service
        session_service = agent_runner._session_service
        session_lock = agent_runner._session_lock

        artifact_service.delete_session_artifacts = mocker.AsyncMock(return_value=2)
        session_service.delete_session = mocker.AsyncMock()
        session_lock.delete = mocker.AsyncMock()

        await agent_runner.delete_session(user_id="user-1", session_id="session-1")

        assert artifact_service.delete_session_artifacts.await_args.kwargs["session_id"] == "session-1"
        assert session_service.delete_session.await_args.kwargs["session_id"] == "session-1"
        assert session_service.delete_session.await_args.kwargs["user_id"] == "user-1"
        session_lock.delete.assert_awaited_once_with(
            app_name=agent_runner._app_name,
            user_id="user-1",
            session_id="session-1"
        )

        artifact_service.delete_session_artifacts.side_effect = RuntimeError("Artifact cleanup failed")
        with pytest.raises(RuntimeError, match="Artifact cleanup failed"):
            await agent_runner.delete_session(user_id="user-1", session_id="session-1")

        artifact_service.delete_session_artifacts.side_effect = None
        session_service.delete_session.side_effect = RuntimeError("Session deletion failed")
        with pytest.raises(RuntimeError, match="Session deletion failed"):
            await agent_runner.delete_session(user_id="user-1", session_id="session-1")

    @pytest.mark.asyncio
    async def test_get_session(self, mocker, agent_runner):
        event = mocker.MagicMock()
        event.timestamp = 1700000000.0

        session = mocker.MagicMock(
            id="session-1",
            app_name="data_agent",
            user_id="user-1",
            state={},
            events=[event],
            last_update_time=1700000001.0
        )
        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=session)
        agent_runner._session_lock.get_run_state = mocker.AsyncMock(return_value=RunState.IDLE)
        result = await agent_runner.get_session(user_id="user-1", session_id="session-1")

        assert result.session_id == "session-1"
        assert result.last_update_time.timestamp() == 1700000001.0
        assert result.run_state == RunState.IDLE
        assert event.timestamp.timestamp() == 1700000000.0

        event.timestamp = 1700000000.0
        agent_runner._session_lock.get_run_state.return_value = RunState.RUNNING
        result = await agent_runner.get_session(user_id="user-1", session_id="session-1")
        assert result.run_state == RunState.RUNNING

        agent_runner._session_service.get_session.return_value = None
        with pytest.raises(ValueError):
            await agent_runner.get_session(user_id="user-1", session_id="session-1")

        agent_runner._session_service.get_session.side_effect = RuntimeError("Session retrieval failed")

        with pytest.raises(RuntimeError, match="Session retrieval failed"):
            await agent_runner.get_session(user_id="user-1", session_id="session-1")

    @pytest.mark.asyncio
    async def test_load_session_artifact(self, mocker, agent_runner):
        artifact_service = agent_runner._artifact_service

        artifact = mocker.MagicMock()
        artifact.inline_data.data = b"image bytes"
        artifact.inline_data.mime_type = "image/png"

        artifact_service.load_artifact = mocker.AsyncMock(return_value=artifact)
        artifact_service.parse_version = mocker.MagicMock(return_value=2)

        request = LoadSessionArtifactRequest(
            data_uri="data_agent/user-1/session-1/chart.png/2",
            filename="chart.png",
            media_type="image/jpeg"
        )

        result = await agent_runner.load_session_artifact(
            user_id="user-1",
            session_id="session-1",
            request=request
        )

        assert result.content == b"image bytes"
        assert result.media_type == "image/png"

        artifact.inline_data.mime_type = None
        result = await agent_runner.load_session_artifact(
            user_id="user-1",
            session_id="session-1",
            request=request
        )
        assert result.media_type == "image/jpeg"

        artifact.inline_data = None
        with pytest.raises(ValueError):
            await agent_runner.load_session_artifact(
                user_id="user-1",
                session_id="session-1",
                request=request
            )

        artifact_service.load_artifact.return_value = None
        with pytest.raises(ValueError):
            await agent_runner.load_session_artifact(
                user_id="user-1",
                session_id="session-1",
                request=request
            )

        artifact_service.load_artifact.side_effect = RuntimeError("Storage failed")
        with pytest.raises(RuntimeError, match="Storage failed"):
            await agent_runner.load_session_artifact(
                user_id="user-1",
                session_id="session-1",
                request=request
            )

        artifact_service.load_artifact.reset_mock()
        artifact_service.load_artifact.side_effect = None
        artifact_service.load_artifact.return_value = artifact
        artifact_service.parse_version.side_effect = ValueError("no version")

        with pytest.raises(ValueError, match="no version"):
            await agent_runner.load_session_artifact(
                user_id="user-1",
                session_id="session-1",
                request=request
            )

    @pytest.mark.asyncio
    async def test_get_session_run_state(self, mocker, agent_runner):
        session_lock = agent_runner._session_lock
        session_lock.get_run_state = mocker.AsyncMock(return_value=RunState.RUNNING)

        result = await agent_runner.get_session_run_state(user_id="user-1", session_id="session-1")

        assert result.run_state == RunState.RUNNING

        session_lock.get_run_state.return_value = RunState.IDLE
        result = await agent_runner.get_session_run_state(user_id="user-1", session_id="session-1")

        assert result.run_state == RunState.IDLE

        session_lock.get_run_state.side_effect = RuntimeError("Failed to retrieve run state")
        with pytest.raises(RuntimeError, match="Failed to retrieve run state"):
            await agent_runner.get_session_run_state(user_id="user-1", session_id="session-1")

    @pytest.mark.asyncio
    async def test_rename_session_title(self, mocker, agent_runner):
        session = mocker.MagicMock()
        session_service = agent_runner._session_service
        session_lock = agent_runner._session_lock

        session_service.get_session = mocker.AsyncMock(return_value=session)
        session_lock.get_run_state = mocker.AsyncMock(return_value=RunState.IDLE)
        request = RenameSessionRequest(session_title="Greetings")

        await agent_runner.rename_session_title(
            user_id="user-1",
            session_id="session-1",
            request=request
        )

        session_service.get_session.assert_awaited_once_with(
            app_name=agent_runner._app_name,
            user_id="user-1",
            session_id="session-1"
        )

        session_service.get_session.reset_mock()
        session_lock.get_run_state.return_value = RunState.RUNNING
        with pytest.raises(ValueError):
            await agent_runner.rename_session_title(
                user_id="user-1",
                session_id="session-1",
                request=request
            )

        session_service.get_session.assert_not_awaited()

        session_lock.get_run_state.return_value = RunState.IDLE
        session_service.get_session.return_value = None
        with pytest.raises(ValueError):
            await agent_runner.rename_session_title(
                user_id="user-1",
                session_id="session-1",
                request=request
            )

    @pytest.mark.asyncio
    async def test_create_session_title(self, mocker, agent_runner):
        session = mocker.MagicMock()
        session.events = [_build_event(mocker, "user", ["Hello"])]

        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=session)
        agent_runner._title_generator.generate = mocker.AsyncMock(return_value="Greetings")
        agent_runner._session_lock.get_run_state = mocker.AsyncMock(return_value=RunState.IDLE)
        result = await agent_runner.create_session_title(user_id="user-1", session_id="session-1")

        assert result.session_title == "Greetings"
        assert agent_runner._title_generator.generate.await_args.kwargs["user_message"] == "Hello"

        await agent_runner.create_session_title(
            user_id="user-1",
            session_id="session-1",
            user_prompt="What are your capabilities?"
        )
        assert agent_runner._title_generator.generate.await_args.kwargs["user_message"] == "What are your capabilities?"
        session.events = []

        with pytest.raises(ValueError):
            await agent_runner.create_session_title(user_id="user-1", session_id="session-1")

        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=None)

        with pytest.raises(ValueError):
            await agent_runner.create_session_title(user_id="user-1", session_id="session-1")

    @pytest.mark.asyncio
    async def test_run(self, mocker, agent_runner):
        data_uri = "data_agent/user-1/session-1/photo.png/1"
        agent_runner._build_user_content = mocker.AsyncMock(return_value=mocker.MagicMock())
        agent_runner._get_agent_response = mocker.AsyncMock(return_value=("Success response", 1700000000.0))
        agent_runner._record_run_error = mocker.AsyncMock()

        agent_runner._session_lock.acquire = mocker.AsyncMock(return_value=True)
        agent_runner._session_lock.release = mocker.AsyncMock()

        mock_image_file = mocker.MagicMock(spec=UploadFile)
        request = RunAgentRequest(query="Compare the datasets")

        result = await agent_runner.run(
            user_id="user-1",
            session_id="session-1",
            request=request,
            image_file=mock_image_file
        )

        assert result.response == "Success response"
        assert result.timestamp.timestamp() == 1700000000.0

        agent_runner._session_lock.acquire.assert_awaited_once_with(agent_runner._app_name, "user-1", "session-1")
        agent_runner._build_user_content.assert_awaited_once_with(
            "user-1",
            "session-1",
            "Compare the datasets",
            mock_image_file
        )
        agent_runner._session_lock.release.assert_awaited_once_with(
            app_name=agent_runner._app_name,
            user_id="user-1",
            session_id="session-1"
        )

        agent_runner._session_lock.acquire.reset_mock()
        agent_runner._session_lock.release.reset_mock()
        agent_runner._session_lock.acquire.return_value = False

        with pytest.raises(ValueError):
            await agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=request,
                image_file=mock_image_file
            )

        agent_runner._session_lock.release.assert_awaited_once_with(
            app_name=agent_runner._app_name,
            user_id="user-1",
            session_id="session-1"
        )

        agent_runner._session_lock.acquire.return_value = True
        agent_runner._get_agent_response.side_effect = RuntimeError("Runtime error")

        with pytest.raises(RuntimeError):
            await agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=request,
                image_file=mock_image_file
            )

        agent_runner._record_run_error.assert_awaited_once()
        assert isinstance(agent_runner._record_run_error.call_args[0][2], RuntimeError)
