import pytest
import asyncio

from common.constants import AppNames
from data_agent.agents import system_agent
from data_agent.agents.plugins import TimingLoggerPlugin
from data_agent.services.title_generator import TitleGenerator


def _final_event(mocker, text):
    event = mocker.MagicMock()
    event.is_final_response.return_value = True
    event.content.parts = [mocker.MagicMock(text=text)]
    return event


class TestTitleGenerator:
    @pytest.fixture
    def title_generator(self, mocker):
        session_service = mocker.MagicMock()
        session_service.create_session = mocker.AsyncMock(return_value=mocker.MagicMock(id="system-session-1"))
        session_service.delete_session = mocker.AsyncMock()
        mocker.patch("data_agent.services.title_generator.InMemorySessionService", return_value=session_service)
        mocker.patch("data_agent.services.title_generator.Runner", return_value=mocker.MagicMock())
        return TitleGenerator()

    def test_init(self, mocker):
        session_service_cls = mocker.patch("data_agent.services.title_generator.InMemorySessionService")
        runner_cls = mocker.patch("data_agent.services.title_generator.Runner")

        title_generator = TitleGenerator()

        kwargs = runner_cls.call_args.kwargs
        assert kwargs["agent"] is system_agent
        assert kwargs["app_name"] == AppNames.SYSTEM
        assert kwargs["session_service"] is session_service_cls.return_value
        assert [type(plugin) for plugin in kwargs["plugins"]] == [TimingLoggerPlugin]
        assert title_generator._session_service is session_service_cls.return_value
        assert title_generator._runner is runner_cls.return_value

    def test_generate(self, mocker, title_generator):
        async def _events():
            yield _final_event(mocker, "Greetings")

        title_generator._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())

        title = asyncio.run(title_generator.generate(
            user_id="user-1",
            session_id="session-1",
            user_message="Hello, how are you?"
        ))

        assert title == "Greetings"
        create_kwargs = title_generator._session_service.create_session.await_args.kwargs
        assert create_kwargs == {"app_name": AppNames.SYSTEM, "user_id": "user-1"}

        run_kwargs = title_generator._runner.run_async.call_args.kwargs
        assert run_kwargs["user_id"] == "user-1"
        assert run_kwargs["session_id"] == "system-session-1"
        assert run_kwargs["new_message"].role == "user"
        assert run_kwargs["new_message"].parts[0].text == "Hello, how are you?"

        title_generator._session_service.delete_session.assert_awaited_once_with(
            app_name=AppNames.SYSTEM,
            user_id="user-1",
            session_id="system-session-1"
        )

        async def _empty_events():
            yield _final_event(mocker, "")

        title_generator._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _empty_events())

        with pytest.raises(ValueError, match="create session title"):
            asyncio.run(
                title_generator.generate(
                    user_id="user-1",
                    session_id="session-1",
                    user_message="Hello, how are you?"
                )
            )
        assert title_generator._session_service.delete_session.await_count == 2

    def test_generate_skips_final_events_without_content(self, mocker, title_generator):
        async def _events():
            event = mocker.MagicMock()
            event.is_final_response.return_value = False
            event.content.parts = [mocker.MagicMock(text="Partial")]
            yield event

            empty = mocker.MagicMock()
            empty.is_final_response.return_value = True
            empty.content = None
            yield empty

            yield _final_event(mocker, "Greetings")

        title_generator._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())

        title = asyncio.run(title_generator.generate(
            user_id="user-1",
            session_id="session-1",
            user_message="Hello, how are you?"
        ))

        assert title == "Greetings"

        async def _no_final_events():
            event = mocker.MagicMock()
            event.is_final_response.return_value = False
            yield event

        title_generator._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _no_final_events())

        with pytest.raises(ValueError, match="create session title"):
            asyncio.run(title_generator.generate(
                user_id="user-1",
                session_id="session-1",
                user_message="Hello, how are you?"
            ))

    def test_generate_deletes_scratch_session_when_runner_fails(self, mocker, title_generator):
        title_generator._runner.run_async = mocker.MagicMock(side_effect=Exception("Runtime error"))

        with pytest.raises(Exception, match="Runtime error"):
            asyncio.run(title_generator.generate(
                user_id="user-1",
                session_id="session-1",
                user_message="Hello, how are you?"
            ))

        title_generator._session_service.delete_session.assert_awaited_once()

    def test_generate_fails_when_scratch_session_cannot_be_created(self, mocker, title_generator):
        title_generator._session_service.create_session = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        title_generator._runner.run_async = mocker.MagicMock()

        with pytest.raises(Exception, match="Runtime error"):
            asyncio.run(title_generator.generate(
                user_id="user-1",
                session_id="session-1",
                user_message="Hello, how are you?"
            ))

        title_generator._runner.run_async.assert_not_called()
        title_generator._session_service.delete_session.assert_not_awaited()

    def test_generate_closes_event_stream_after_first_title(self, mocker, title_generator):
        closed = []

        async def _events():
            try:
                yield _final_event(mocker, "Greetings")
                yield _final_event(mocker, "Late title")
            finally:
                closed.append(True)

        title_generator._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())

        async def _generate():
            title = await title_generator.generate(
                user_id="user-1",
                session_id="session-1",
                user_message="Hello, how are you?"
            )
            return title, list(closed)

        title, closed_before_loop_shutdown = asyncio.run(_generate())

        assert title == "Greetings"
        assert closed_before_loop_shutdown == [True]
