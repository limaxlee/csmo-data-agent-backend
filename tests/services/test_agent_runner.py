import pytest
import asyncio

from common.constants import AppNames, ArtifactPrefix, EventAuthors, SessionStateFields, RunState, CONTENT_TYPE
from common.exceptions import SessionBusyError
from data_agent.agents.plugins import TimingLoggerPlugin
from data_agent.services.agent_runner import AgentRunner
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


def _final_event(mocker, text="Hi", timestamp=1700000000.0):
    event = mocker.MagicMock()
    event.is_final_response.return_value = True
    event.timestamp = timestamp
    event.content.parts = [mocker.MagicMock(text=text)]
    return event


class TestAgentRunner:
    @pytest.fixture
    def agent_runner(self, mocker):
        mocker.patch("data_agent.services.agent_runner.Runner", return_value=mocker.MagicMock())

        session_service = mocker.MagicMock()
        session_service.get_session = mocker.AsyncMock(return_value=None)
        session_service.append_event = mocker.AsyncMock()

        lock_repository = mocker.MagicMock()
        lock_repository.try_acquire = mocker.AsyncMock(return_value=True)
        lock_repository.release = mocker.AsyncMock(return_value=True)
        lock_repository.delete = mocker.AsyncMock()
        lock_repository.get_run_state = mocker.AsyncMock(return_value=RunState.IDLE)
        lock_repository.get_run_states = mocker.AsyncMock(return_value={})

        return AgentRunner(
            agent=mocker.MagicMock(),
            session_service=session_service,
            artifact_service=mocker.MagicMock(),
            title_generator=mocker.MagicMock(),
            lock_repository=lock_repository
        )

    def test_init(self, mocker):
        runner_cls = mocker.patch("data_agent.services.agent_runner.Runner")
        agent = mocker.MagicMock()
        session_service = mocker.MagicMock()
        artifact_service = mocker.MagicMock()
        title_generator = mocker.MagicMock()
        lock_repository = mocker.MagicMock()

        agent_runner = AgentRunner(
            agent=agent,
            session_service=session_service,
            artifact_service=artifact_service,
            title_generator=title_generator,
            lock_repository=lock_repository
        )

        kwargs = runner_cls.call_args.kwargs
        assert kwargs["agent"] is agent
        assert kwargs["app_name"] == AppNames.ROOT
        assert kwargs["session_service"] is session_service
        assert kwargs["artifact_service"] is artifact_service
        assert [type(plugin) for plugin in kwargs["plugins"]] == [TimingLoggerPlugin]
        assert agent_runner._app_name == AppNames.ROOT
        assert agent_runner._runner is runner_cls.return_value
        assert agent_runner._session_service is session_service
        assert agent_runner._artifact_service is artifact_service
        assert agent_runner._title_generator is title_generator
        assert agent_runner._lock_repository is lock_repository

    def test_find_last_user_message(self, mocker, agent_runner):
        session = mocker.MagicMock()
        session.events = [
            _build_event(mocker, "user", ["Hello"]),
            _build_event(mocker, "root_orchestrator", ["Hi there"]),
            _build_event(mocker, "user", ["  ", "How many models?"]),
            _build_event(mocker, "user", None),
            _build_event(mocker, "user", [""])
        ]

        assert agent_runner._find_last_user_message(session) == "How many models?"

        session.events = [_build_event(mocker, "root_orchestrator", ["Hi there"])]
        assert agent_runner._find_last_user_message(session) is None

    def test_set_title(self, mocker, agent_runner):
        session = mocker.MagicMock()

        asyncio.run(agent_runner._set_title(session, "Greetings"))

        recorded_session, event = agent_runner._session_service.append_event.await_args.args
        assert recorded_session is session
        assert event.author == EventAuthors.SYSTEM
        assert event.actions.state_delta == {SessionStateFields.TITLE: "Greetings"}

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
        save_kwargs = agent_runner._artifact_service.save_artifact.await_args.kwargs
        assert save_kwargs["filename"] == "chart.png"
        assert save_kwargs["artifact"].inline_data.data == b"image bytes"
        assert save_kwargs["artifact"].inline_data.mime_type == "image/png"
        assert agent_runner._artifact_service.get_object_key.call_args.kwargs["version"] == 2

        image_file.content_type = None
        asyncio.run(agent_runner._upload_artifact(
            user_id="user-1",
            session_id="session-1",
            image_file=image_file
        ))
        save_kwargs = agent_runner._artifact_service.save_artifact.await_args.kwargs
        assert save_kwargs["artifact"].inline_data.mime_type == CONTENT_TYPE

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
        assert result.sessions[0].run_state == RunState.IDLE
        assert agent_runner._lock_repository.get_run_states.await_args.kwargs["session_ids"] == ["session-1"]

        agent_runner._lock_repository.get_run_states = mocker.AsyncMock(return_value={"session-1": RunState.RUNNING})
        result = asyncio.run(agent_runner.list_sessions(user_id="user-1"))
        assert result.sessions[0].run_state == RunState.RUNNING

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

        agent_runner._session_service.create_session = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        with pytest.raises(Exception):
            asyncio.run(agent_runner.create_session(user_id="user-1"))

    def test_create_session_title(self, mocker, agent_runner):
        session = mocker.MagicMock()
        session.events = [_build_event(mocker, "user", ["Hello"])]
        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=session)
        agent_runner._title_generator.generate = mocker.AsyncMock(return_value="Greetings")
        set_title = mocker.patch.object(agent_runner, "_set_title", new=mocker.AsyncMock())

        result = asyncio.run(agent_runner.create_session_title(user_id="user-1", session_id="session-1"))

        assert result.session_title == "Greetings"
        assert agent_runner._title_generator.generate.await_args.kwargs["user_message"] == "Hello"
        set_title.assert_awaited_once_with(session, "Greetings")

        asyncio.run(
            agent_runner.create_session_title(
                user_id="user-1",
                session_id="session-1",
                user_message="What are your capabilities?"
            )
        )
        assert agent_runner._title_generator.generate.await_args.kwargs["user_message"] == \
               "What are your capabilities?"

        session.events = []
        with pytest.raises(ValueError):
            asyncio.run(agent_runner.create_session_title(user_id="user-1", session_id="session-1"))

        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=None)
        with pytest.raises(ValueError):
            asyncio.run(agent_runner.create_session_title(user_id="user-1", session_id="session-1"))

    def test_create_session_title_rejected_while_running(self, mocker, agent_runner):
        agent_runner._lock_repository.get_run_state = mocker.AsyncMock(return_value=RunState.RUNNING)
        agent_runner._session_service.get_session = mocker.AsyncMock()
        agent_runner._title_generator.generate = mocker.AsyncMock()

        with pytest.raises(SessionBusyError):
            asyncio.run(agent_runner.create_session_title(user_id="user-1", session_id="session-1"))

        agent_runner._session_service.get_session.assert_not_awaited()
        agent_runner._title_generator.generate.assert_not_awaited()

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

    def test_rename_session_title_rejected_while_running(self, mocker, agent_runner):
        agent_runner._lock_repository.get_run_state = mocker.AsyncMock(return_value=RunState.RUNNING)
        agent_runner._session_service.get_session = mocker.AsyncMock()

        with pytest.raises(SessionBusyError):
            asyncio.run(agent_runner.rename_session_title(
                user_id="user-1",
                session_id="session-1",
                request=RenameSessionRequest(session_title="Greetings")
            ))

        agent_runner._session_service.get_session.assert_not_awaited()

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
        assert result.run_state == RunState.IDLE
        assert event.timestamp.timestamp() == 1700000000.0

        event.timestamp = 1700000000.0
        agent_runner._lock_repository.get_run_state = mocker.AsyncMock(return_value=RunState.RUNNING)
        result = asyncio.run(agent_runner.get_session(user_id="user-1", session_id="session-1"))
        assert result.run_state == RunState.RUNNING

        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=None)
        with pytest.raises(ValueError):
            asyncio.run(agent_runner.get_session(user_id="user-1", session_id="session-1"))

    def test_get_session_run_state(self, mocker, agent_runner):
        agent_runner._lock_repository.get_run_state = mocker.AsyncMock(return_value=RunState.RUNNING)

        result = asyncio.run(agent_runner.get_session_run_state(user_id="user-1", session_id="session-1"))

        assert result == RunState.RUNNING
        agent_runner._lock_repository.get_run_state.assert_awaited_once_with(
            app_name=agent_runner._app_name,
            user_id="user-1",
            session_id="session-1"
        )

    def test_delete_session(self, mocker, agent_runner):
        agent_runner._artifact_service.delete_session_artifacts = mocker.AsyncMock(return_value=2)
        agent_runner._session_service.delete_session = mocker.AsyncMock()

        asyncio.run(agent_runner.delete_session(user_id="user-1", session_id="session-1"))

        assert agent_runner._artifact_service.delete_session_artifacts.await_args.kwargs["session_id"] == "session-1"
        assert agent_runner._session_service.delete_session.await_args.kwargs["session_id"] == "session-1"
        assert agent_runner._session_service.delete_session.await_args.kwargs["user_id"] == "user-1"
        agent_runner._lock_repository.delete.assert_awaited_once_with(
            app_name=agent_runner._app_name,
            user_id="user-1",
            session_id="session-1"
        )

        agent_runner._session_service.delete_session = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        with pytest.raises(Exception):
            asyncio.run(agent_runner.delete_session(user_id="user-1", session_id="session-1"))

    def test_delete_session_keeps_session_when_artifact_cleanup_fails(self, mocker, agent_runner):
        agent_runner._artifact_service.delete_session_artifacts = mocker.AsyncMock(side_effect=RuntimeError("boom"))
        agent_runner._session_service.delete_session = mocker.AsyncMock()

        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(agent_runner.delete_session(user_id="user-1", session_id="session-1"))

        agent_runner._session_service.delete_session.assert_not_awaited()
        agent_runner._lock_repository.delete.assert_not_awaited()

    def test_load_session_artifact(self, mocker, agent_runner):
        artifact = mocker.MagicMock()
        artifact.inline_data.data = b"image bytes"
        artifact.inline_data.mime_type = "image/png"
        agent_runner._artifact_service.load_artifact = mocker.AsyncMock(return_value=artifact)
        agent_runner._artifact_service.parse_version = mocker.MagicMock(return_value=2)
        request = LoadSessionArtifactRequest(
            data_uri="data_agent/user-1/session-1/chart.png/2",
            filename="chart.png",
            media_type="image/jpeg"
        )

        result = asyncio.run(agent_runner.load_session_artifact(
            user_id="user-1",
            session_id="session-1",
            request=request
        ))

        assert result.content == b"image bytes"
        assert result.media_type == "image/png"
        assert agent_runner._artifact_service.parse_version.call_args.args == (request.data_uri,)
        assert agent_runner._artifact_service.load_artifact.await_args.kwargs["filename"] == "chart.png"
        assert agent_runner._artifact_service.load_artifact.await_args.kwargs["version"] == 2

        artifact.inline_data.mime_type = None
        result = asyncio.run(agent_runner.load_session_artifact(
            user_id="user-1",
            session_id="session-1",
            request=request
        ))
        assert result.media_type == "image/jpeg"

        artifact.inline_data = None
        with pytest.raises(ValueError):
            asyncio.run(agent_runner.load_session_artifact(
                user_id="user-1",
                session_id="session-1",
                request=request
            ))

        agent_runner._artifact_service.load_artifact = mocker.AsyncMock(return_value=None)
        with pytest.raises(ValueError):
            asyncio.run(agent_runner.load_session_artifact(
                user_id="user-1",
                session_id="session-1",
                request=request
            ))

        agent_runner._artifact_service.load_artifact = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        with pytest.raises(Exception):
            asyncio.run(agent_runner.load_session_artifact(
                user_id="user-1",
                session_id="session-1",
                request=request
            ))

        agent_runner._artifact_service.parse_version = mocker.MagicMock(side_effect=ValueError("no version"))
        agent_runner._artifact_service.load_artifact = mocker.AsyncMock(return_value=artifact)
        with pytest.raises(ValueError, match="no version"):
            asyncio.run(agent_runner.load_session_artifact(
                user_id="user-1",
                session_id="session-1",
                request=request
            ))
        agent_runner._artifact_service.load_artifact.assert_not_awaited()

    def test_run(self, mocker, agent_runner):
        async def _events():
            yield _final_event(mocker, "Hello, how can I help you?")

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())
        create_title = mocker.patch.object(agent_runner, "_create_session_title", new=mocker.AsyncMock())

        result = asyncio.run(
            agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="Hello")
            )
        )

        assert result.response == "Hello, how can I help you?"
        assert result.timestamp.timestamp() == 1700000000.0
        run_kwargs = agent_runner._runner.run_async.call_args.kwargs
        assert run_kwargs["user_id"] == "user-1"
        assert run_kwargs["session_id"] == "session-1"
        assert run_kwargs["new_message"].role == EventAuthors.USER
        assert run_kwargs["new_message"].parts[0].text == "Hello"
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
        parts = agent_runner._runner.run_async.call_args.kwargs["new_message"].parts
        assert parts[-1].text == "What is in this chart?"
        assert f"{ArtifactPrefix.DATA_URI}: data_agent/u/s/chart.png/0" in parts[0].text
        assert f"{ArtifactPrefix.FILENAME}: chart.png" in parts[0].text
        assert f"{ArtifactPrefix.CONTENT_TYPE}: image/png" in parts[0].text

        asyncio.run(
            agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="Hello", new_session=True)
            )
        )
        create_title.assert_awaited_once_with(user_id="user-1", session_id="session-1", user_message="Hello")

        create_title_failing = mocker.patch.object(
            agent_runner, "_create_session_title", new=mocker.AsyncMock(side_effect=Exception("Runtime error"))
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

    def test_run_without_final_content(self, mocker, agent_runner):
        escalated_event = mocker.MagicMock()
        escalated_event.is_final_response.return_value = True
        escalated_event.timestamp = 1700000000.0
        escalated_event.content = None
        escalated_event.actions.escalate = True
        escalated_event.error_message = "Tool crashed"

        async def _events():
            yield escalated_event

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())

        result = asyncio.run(
            agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="Hello")
            )
        )
        assert result.response == "Agent escalated: Tool crashed"

        escalated_event.error_message = None
        result = asyncio.run(
            agent_runner.run(user_id="user-1", session_id="session-1", request=RunAgentRequest(query="Hello"))
        )
        assert result.response == "Agent escalated: No specific message."

        async def _empty_final_events():
            event = mocker.MagicMock()
            event.is_final_response.return_value = False
            event.timestamp = 1600000000.0
            yield event
            yield escalated_event

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _empty_final_events())
        escalated_event.actions.escalate = False

        result = asyncio.run(
            agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="Hello")
            )
        )
        assert result.response == ""
        assert result.timestamp.timestamp() == 1700000000.0

        async def _no_final_events():
            event = mocker.MagicMock()
            event.is_final_response.return_value = False
            yield event

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _no_final_events())

        with pytest.raises(RuntimeError, match="no final response"):
            asyncio.run(
                agent_runner.run(user_id="user-1", session_id="session-1", request=RunAgentRequest(query="Hello"))
            )
        agent_runner._lock_repository.release.assert_awaited()

    def test_run_closes_event_stream_after_final_response(self, mocker, agent_runner):
        closed = []

        async def _events():
            try:
                yield _final_event(mocker, "Hi")
                yield _final_event(mocker, "Late answer")
            finally:
                closed.append(True)

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())

        async def _run():
            result = await agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="Hello")
            )
            return result, list(closed)

        result, closed_before_loop_shutdown = asyncio.run(_run())

        assert result.response == "Hi"
        assert closed_before_loop_shutdown == [True]

    def test_run_records_error_in_session(self, mocker, agent_runner):
        agent_runner._runner.run_async = mocker.MagicMock(side_effect=Exception("Runtime error"))
        session = mocker.MagicMock()
        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=session)

        with pytest.raises(Exception, match="Runtime error"):
            asyncio.run(
                agent_runner.run(user_id="user-1", session_id="session-1", request=RunAgentRequest(query="Hello"))
            )

        recorded_session, error_event = agent_runner._session_service.append_event.await_args.args
        assert recorded_session is session
        assert error_event.author == EventAuthors.SYSTEM
        assert error_event.error_code == "LLM_ERROR"
        assert error_event.error_message == "Runtime error"
        agent_runner._lock_repository.release.assert_awaited_once()

        agent_runner._session_service.append_event = mocker.AsyncMock(side_effect=Exception("DB down"))
        with pytest.raises(Exception, match="Runtime error"):
            asyncio.run(
                agent_runner.run(user_id="user-1", session_id="session-1", request=RunAgentRequest(query="Hello"))
            )

        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=None)
        agent_runner._session_service.append_event = mocker.AsyncMock()
        with pytest.raises(Exception, match="Runtime error"):
            asyncio.run(
                agent_runner.run(user_id="user-1", session_id="session-1", request=RunAgentRequest(query="Hello"))
            )
        agent_runner._session_service.append_event.assert_not_awaited()

    def test_run_rejects_when_session_busy(self, mocker, agent_runner):
        agent_runner._lock_repository.try_acquire = mocker.AsyncMock(return_value=False)
        agent_runner._runner.run_async = mocker.MagicMock()
        create_title = mocker.patch.object(agent_runner, "_create_session_title", new=mocker.AsyncMock())

        with pytest.raises(SessionBusyError):
            asyncio.run(
                agent_runner.run(
                    user_id="user-1",
                    session_id="session-1",
                    request=RunAgentRequest(query="Hello", new_session=True)
                )
            )

        agent_runner._lock_repository.try_acquire.assert_awaited_once_with(agent_runner._app_name, "user-1", "session-1")
        agent_runner._runner.run_async.assert_not_called()
        create_title.assert_not_awaited()
        agent_runner._lock_repository.release.assert_not_awaited()

    def test_run_releases_lock_on_success_and_failure(self, mocker, agent_runner):
        async def _events():
            yield _final_event(mocker, "Hi")

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())
        asyncio.run(agent_runner.run(user_id="user-1", session_id="session-1", request=RunAgentRequest(query="Hello")))
        agent_runner._lock_repository.release.assert_awaited_once_with(agent_runner._app_name, "user-1", "session-1")

        agent_runner._lock_repository.release.reset_mock()
        agent_runner._runner.run_async = mocker.MagicMock(side_effect=Exception("Runtime error"))
        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=None)
        with pytest.raises(Exception):
            asyncio.run(
                agent_runner.run(user_id="user-1", session_id="session-1", request=RunAgentRequest(query="Hello"))
            )
        agent_runner._lock_repository.release.assert_awaited_once()

    def test_run_creates_title_even_though_session_is_running(self, mocker, agent_runner):
        # Inside run() the lock is held, so the state is RUNNING. The in-run
        # title creation must bypass the busy check that guards the endpoint.
        agent_runner._lock_repository.get_run_state = mocker.AsyncMock(return_value=RunState.RUNNING)

        async def _events():
            yield _final_event(mocker, "Hi")

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())
        session = mocker.MagicMock()
        session.events = []
        agent_runner._session_service.get_session = mocker.AsyncMock(return_value=session)
        agent_runner._title_generator.generate = mocker.AsyncMock(return_value="Greetings")
        set_title = mocker.patch.object(agent_runner, "_set_title", new=mocker.AsyncMock())

        asyncio.run(
            agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="Hello", new_session=True)
            )
        )

        assert agent_runner._title_generator.generate.await_args.kwargs["user_message"] == "Hello"
        set_title.assert_awaited_once_with(session, "Greetings")

    def test_run_creates_title_before_releasing_lock(self, mocker, agent_runner):
        async def _events():
            yield _final_event(mocker, "Hi")

        order = []

        async def _create_title(**kwargs):
            order.append("title")

        async def _release(*args):
            order.append("release")
            return True

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())
        mocker.patch.object(agent_runner, "_create_session_title", new=mocker.AsyncMock(side_effect=_create_title))
        agent_runner._lock_repository.release = mocker.AsyncMock(side_effect=_release)

        asyncio.run(
            agent_runner.run(
                user_id="user-1",
                session_id="session-1",
                request=RunAgentRequest(query="Hello", new_session=True)
            )
        )

        assert order == ["title", "release"]

    def test_run_release_failure_does_not_mask_result(self, mocker, agent_runner):
        async def _events():
            yield _final_event(mocker, "Hi")

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())
        agent_runner._lock_repository.release = mocker.AsyncMock(return_value=False)

        result = asyncio.run(
            agent_runner.run(user_id="user-1", session_id="session-1", request=RunAgentRequest(query="Hello"))
        )

        assert result.response == "Hi"
        agent_runner._lock_repository.release.assert_awaited_once()
