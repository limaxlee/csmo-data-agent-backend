import pytest
import asyncio

from common.constants import ArtifactPrefix, SessionStateFields
from data_agent.runners import RootAgentRunner
from data_agent.schemas import RenameSessionRequest, RunAgentRequest, LoadSessionArtifactRequest


def _build_event(mocker, author, texts):
    event = mocker.MagicMock()
    event.author = author
    if texts is None:
        event.content = None
    else:
        event.content = mocker.MagicMock()
        event.content.parts = [mocker.MagicMock(text=text) for text in texts]
    return event


class TestRootAgentRunner:
    @pytest.fixture
    def agent_runner(self, mocker):
        session_service = mocker.MagicMock()
        adk_runner = mocker.MagicMock()
        mocker.patch("data_agent.runners.root_agent.DatabaseSessionService", return_value=session_service)
        mocker.patch("data_agent.runners.root_agent.Runner", return_value=adk_runner)

        return RootAgentRunner(
            artifact_service=mocker.MagicMock(),
            system_runner=mocker.MagicMock()
        )

    def test_upload_artifact(self, mocker, agent_runner):
        image_file = mocker.MagicMock(filename="chart.png", content_type="image/png")
        image_file.read = mocker.AsyncMock(return_value=b"image bytes")
        agent_runner._artifact_service.save_artifact = mocker.AsyncMock(return_value=2)
        agent_runner._artifact_service.get_object_key = mocker.MagicMock(return_value="data_agent/u/s/chart.png/2")

        data_uri = asyncio.run(agent_runner._upload_artifact(
            user_id="user-1",
            session_id="session-1",
            image_file=image_file
        ))

        assert data_uri == "data_agent/u/s/chart.png/2"
        assert agent_runner._artifact_service.save_artifact.await_args.kwargs["filename"] == "chart.png"
        assert agent_runner._artifact_service.get_object_key.call_args.kwargs["version"] == 2

        image_file.read = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        with pytest.raises(Exception):
            asyncio.run(agent_runner._upload_artifact(
                user_id="user-1",
                session_id="session-1",
                image_file=image_file
            ))

    def test_list_sessions(self, mocker, agent_runner):
        session = mocker.MagicMock(
            id="session-1",
            app_name="data_agent",
            user_id="user-1",
            state={SessionStateFields.TITLE: "Greetings"},
            events=[],
            last_update_time=1700000000.0
        )
        agent_runner._session_service.list_sessions = mocker.AsyncMock(
            return_value=mocker.MagicMock(sessions=[session])
        )

        result = asyncio.run(agent_runner.list_sessions(user_id="user-1"))

        assert len(result.sessions) == 1
        assert result.sessions[0].session_id == "session-1"
        assert result.sessions[0].state == {SessionStateFields.TITLE: "Greetings"}
        assert result.sessions[0].last_update_time.timestamp() == 1700000000.0

        agent_runner._session_service.list_sessions = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        with pytest.raises(Exception):
            asyncio.run(agent_runner.list_sessions(user_id="user-1"))

    def test_create_session(self, mocker, agent_runner):
        agent_runner._session_service.create_session = mocker.AsyncMock(return_value=mocker.MagicMock(id="session-1"))

        result = asyncio.run(agent_runner.create_session(user_id="user-1"))

        assert result.session_id == "session-1"
        generated_id = agent_runner._session_service.create_session.await_args.kwargs["session_id"]
        assert len(generated_id) == 32
        assert agent_runner._session_service.create_session.await_args.kwargs["user_id"] == "user-1"

    def test_create_session_title(self, mocker, agent_runner):
        session = mocker.MagicMock()
        session.events = [_build_event(mocker, "user", ["Hello"])]
        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=session)
        agent_runner._system_runner.create_session_title = mocker.AsyncMock(return_value="Greetings")
        set_title = mocker.patch.object(agent_runner, "_set_title", new=mocker.AsyncMock())

        result = asyncio.run(agent_runner.create_session_title(user_id="user-1", session_id="session-1"))

        assert result.session_title == "Greetings"
        assert agent_runner._system_runner.create_session_title.await_args.kwargs["user_message"] == "Hello"
        set_title.assert_awaited_once_with(session, "Greetings")

        asyncio.run(
            agent_runner.create_session_title(
                user_id="user-1",
                session_id="session-1",
                user_message="What are your capabilities?"
            )
        )
        assert agent_runner._system_runner.create_session_title.await_args.kwargs["user_message"] == \
               "What are your capabilities?"

        session.events = []
        with pytest.raises(ValueError):
            asyncio.run(agent_runner.create_session_title(user_id="user-1", session_id="session-1"))

        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=None)
        with pytest.raises(ValueError):
            asyncio.run(agent_runner.create_session_title(user_id="user-1", session_id="session-1"))

    def test_rename_session_title(self, mocker, agent_runner):
        session = mocker.MagicMock()
        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=session)
        set_title = mocker.patch.object(agent_runner, "_set_title", new=mocker.AsyncMock())

        asyncio.run(agent_runner.rename_session_title(
            user_id="user-1",
            session_id="session-1",
            request=RenameSessionRequest(session_title="Greetings")
        ))

        set_title.assert_awaited_once_with(session, "Greetings")

        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=None)
        with pytest.raises(ValueError):
            asyncio.run(
                agent_runner.rename_session_title(
                    user_id="user-1",
                    session_id="session-1",
                    request=RenameSessionRequest(session_title="Greetings")
                )
            )

    def test_get_session(self, mocker, agent_runner):
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

        result = asyncio.run(agent_runner.get_session(user_id="user-1", session_id="session-1"))

        assert result.session_id == "session-1"
        assert result.last_update_time.timestamp() == 1700000001.0
        assert event.timestamp.timestamp() == 1700000000.0

        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=None)
        with pytest.raises(ValueError):
            asyncio.run(agent_runner.get_session(user_id="user-1", session_id="session-1"))

    def test_delete_session(self, mocker, agent_runner):
        agent_runner._session_service.delete_session = mocker.AsyncMock()

        asyncio.run(agent_runner.delete_session(user_id="user-1", session_id="session-1"))

        assert agent_runner._session_service.delete_session.await_args.kwargs["session_id"] == "session-1"
        assert agent_runner._session_service.delete_session.await_args.kwargs["user_id"] == "user-1"

        agent_runner._session_service.delete_session = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        with pytest.raises(Exception):
            asyncio.run(agent_runner.delete_session(user_id="user-1", session_id="session-1"))

    def test_load_session_artifact(self, mocker, agent_runner):
        agent_runner._storage = mocker.MagicMock()
        agent_runner._storage.retrieve_object_info = mocker.AsyncMock(return_value={"ContentType": "image/png"})
        agent_runner._storage.retrieve_object = mocker.AsyncMock(return_value=b"image bytes")
        request = LoadSessionArtifactRequest(
            data_uri="data_agent/user-1/session-1/chart.png/0",
            filename="chart.png",
            media_type="image/png"
        )

        result = asyncio.run(agent_runner.load_session_artifact(
            user_id="user-1",
            session_id="session-1",
            request=request
        ))

        assert result.content == b"image bytes"
        assert result.media_type == "image/png"
        assert agent_runner._storage.retrieve_object_info.await_args.kwargs["key"] == \
               "data_agent/user-1/session-1/chart.png/0"
        assert agent_runner._storage.retrieve_object.await_args.args == \
               ("data_agent/user-1/session-1/chart.png/0",)

        agent_runner._storage.retrieve_object_info = mocker.AsyncMock(return_value={})
        result = asyncio.run(agent_runner.load_session_artifact(
            user_id="user-1",
            session_id="session-1",
            request=request
        ))
        assert result.media_type == "application/octet-stream"

        agent_runner._storage.retrieve_object = mocker.AsyncMock(return_value=None)
        with pytest.raises(ValueError):
            asyncio.run(agent_runner.load_session_artifact(
                user_id="user-1",
                session_id="session-1",
                request=request
            ))

        agent_runner._storage.retrieve_object_info = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        with pytest.raises(Exception):
            asyncio.run(agent_runner.load_session_artifact(
                user_id="user-1",
                session_id="session-1",
                request=request
            ))

    def test_run(self, mocker, agent_runner):
        final_event = mocker.MagicMock()
        final_event.is_final_response.return_value = True
        final_event.timestamp = 1700000000.0
        final_event.content.parts = [mocker.MagicMock(text="Hello, how can I help you?")]

        async def _events():
            yield final_event

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())
        create_title = mocker.patch.object(agent_runner, "create_session_title", new=mocker.AsyncMock())

        result = asyncio.run(
            agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="Hello")
            )
        )

        assert result.response == "Hello, how can I help you?"
        assert result.timestamp.timestamp() == 1700000000.0
        sent_message = agent_runner._runner.run_async.call_args.kwargs["new_message"]
        assert sent_message.parts[0].text == "Hello"
        create_title.assert_not_awaited()

        upload = mocker.patch.object(
            agent_runner, "_upload_artifact", new=mocker.AsyncMock(return_value="data_agent/u/s/chart.png/0")
        )
        image_file = mocker.MagicMock(filename="chart.png", content_type="image/png")

        asyncio.run(
            agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="What is in this chart?"),
                image_file=image_file
            )
        )

        upload.assert_awaited_once()
        prompt = agent_runner._runner.run_async.call_args.kwargs["new_message"].parts[0].text
        assert prompt.startswith("What is in this chart?")
        assert f"{ArtifactPrefix.DATA_URI} data_agent/u/s/chart.png/0" in prompt
        assert "chart.png" in prompt

        asyncio.run(
            agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="Hello", new_session=True)
            )
        )
        create_title.assert_awaited_once()

        create_title_failing = mocker.patch.object(
            agent_runner, "create_session_title", new=mocker.AsyncMock(side_effect=Exception("Runtime error"))
        )
        result = asyncio.run(
            agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="Hello", new_session=True)
            )
        )
        assert result.response == "Hello, how can I help you?"
        create_title_failing.assert_awaited_once()

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=Exception("Runtime error"))
        with pytest.raises(Exception):
            asyncio.run(
                agent_runner.run(
                    user_id="user-1",
                    session_id="session-1",
                    request=RunAgentRequest(query="Hello")
                )
            )
