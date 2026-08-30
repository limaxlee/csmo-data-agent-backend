import pytest
import asyncio

from data_agent.runners import SystemAgentRunner


class TestSystemAgentRunner:
    def test_create_session_title(self, mocker):
        agent_runner = SystemAgentRunner()

        session = mocker.MagicMock(id="system-session-1")
        agent_runner._session_service = mocker.MagicMock()
        agent_runner._session_service.create_session = mocker.AsyncMock(return_value=session)
        agent_runner._session_service.delete_session = mocker.AsyncMock()

        final_event = mocker.MagicMock()
        final_event.is_final_response.return_value = True
        final_event.content.parts = [mocker.MagicMock(text="Greetings")]

        async def _events():
            yield final_event

        agent_runner._runner = mocker.MagicMock()
        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _events())

        title = asyncio.run(agent_runner.create_session_title(
            user_id="user-1",
            session_id="session-1",
            user_message="Hello, how are you?"
        ))

        assert title == "Greetings"
        assert agent_runner._runner.run_async.call_args.kwargs["session_id"] == "system-session-1"
        agent_runner._session_service.delete_session.assert_awaited_once()

        empty_event = mocker.MagicMock()
        empty_event.is_final_response.return_value = True
        empty_event.content.parts = [mocker.MagicMock(text="")]

        async def _empty_events():
            yield empty_event

        agent_runner._runner.run_async = mocker.MagicMock(side_effect=lambda **kwargs: _empty_events())

        with pytest.raises(ValueError):
            asyncio.run(
                agent_runner.create_session_title(
                    user_id="user-1",
                    session_id="session-1",
                    user_message="Hello, how are you?"
                )
            )
