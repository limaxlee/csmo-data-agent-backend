import pytest

from common.constants import AppNames
from data_agent.agents import title_agent
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
        assert kwargs["agent"] is title_agent
        assert kwargs["app_name"] == AppNames.TITLE
        assert kwargs["session_service"] is session_service_cls.return_value
        assert title_generator._session_service is session_service_cls.return_value
        assert title_generator._runner is runner_cls.return_value

    @pytest.mark.asyncio
    async def test_generate(self, mocker, title_generator):
        async def _events():
            yield _final_event(mocker, "Greetings")

        title_generator._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())

        title = await title_generator.generate(
            user_id="user-1",
            session_id="session-1",
            user_message="Hello, how are you?"
        )

        assert title == "Greetings"
        create_kwargs = title_generator._session_service.create_session.await_args.kwargs
        assert create_kwargs == {"app_name": AppNames.TITLE, "user_id": "user-1"}

        run_kwargs = title_generator._runner.run_async.call_args.kwargs
        assert run_kwargs["user_id"] == "user-1"
        assert run_kwargs["session_id"] == "system-session-1"
        assert run_kwargs["new_message"].role == "user"
        assert run_kwargs["new_message"].parts[0].text == "Hello, how are you?"

        title_generator._session_service.delete_session.assert_awaited_once_with(
            app_name=AppNames.TITLE,
            user_id="user-1",
            session_id="system-session-1"
        )

        async def _empty_events():
            yield _final_event(mocker, "")

        title_generator._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _empty_events())

        with pytest.raises(ValueError, match="create session title"):
            await title_generator.generate(
                user_id="user-1",
                session_id="session-1",
                user_message="Hello, how are you?"
            )
        assert title_generator._session_service.delete_session.await_count == 2
