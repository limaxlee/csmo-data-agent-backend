import logging
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from common.constants import AppNames
from data_agent.agents import system_agent

logger = logging.getLogger(__name__)


class SystemAgentRunner:
    def __init__(self):
        self._app_name = AppNames.SYSTEM
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=system_agent,
            app_name=AppNames.SYSTEM,
            session_service=self._session_service
        )

    async def create_session_title(self, user_id: str, session_id: str, user_message: str) -> str:
        try:
            session_title = ""
            session = await self._session_service.create_session(app_name=self._app_name, user_id=user_id)
            content = types.Content(role="user", parts=[types.Part(text=user_message)])

            async for event in self._runner.run_async(
                    user_id=user_id,
                    session_id=session.id,
                    new_message=content
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        session_title = event.content.parts[-1].text

            if not session_title:
                raise ValueError(f"Couldn't create session title for session {session_id}")

            await self._session_service.delete_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session.id
            )

            logger.info(f"Created a title {session_title} for session {session_id} of user {user_id}")
            return session_title
        except Exception as e:
            logger.exception(f"Failed to create a title for session {session_id} of user {user_id}: {str(e)}")
            raise
