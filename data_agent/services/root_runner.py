import time
import logging
from fastapi import UploadFile
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.genai import types

from common.constants import (
    ROOT_APP_NAME, SESSION_TITLE_KEY, DATA_URI_PREFIX,
    FILENAME_PREFIX, CONTENT_TYPE
)
from data_agent.agents import root_agent
from data_agent.schemas import RunAgentRequest, RunAgentResponse
from data_agent.services.db_session import PostgreSQLSessionService
from data_agent.services.os_artifact import OSArtifactService
from data_agent.utils import convert_unix_to_datetime

logger = logging.getLogger(__name__)


class RootAgentRunner:
    def __init__(
            self,
            session_service: BaseSessionService,
            artifact_service: OSArtifactService,
            db_session_service: PostgreSQLSessionService
    ):
        self._app_name = ROOT_APP_NAME
        self._session_service = session_service
        self._artifact_service = artifact_service
        self._db_session_service = db_session_service
        self._runner = Runner(
            agent=root_agent,
            app_name=ROOT_APP_NAME,
            session_service=session_service,
            artifact_service=artifact_service
        )

    async def _upload_artifact(self, user_id: str, session_id: str, image_file: UploadFile) -> str:
        filename = image_file.filename
        try:
            image_bytes = await image_file.read()
            content_type = image_file.content_type or "image/jpeg"

            version = await self._artifact_service.save_artifact(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                artifact=types.Part.from_bytes(data=image_bytes, mime_type=content_type)
            )
            data_uri = self._artifact_service.get_object_key(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                version=version
            )

            logger.info(f"Uploaded artifact {filename} with key {data_uri} for user {user_id} and session {session_id}")
            return data_uri
        except Exception as e:
            logger.exception(f"Failed to upload artifact {filename} session {session_id} of user {user_id}: {str(e)}")
            raise

    async def create_session_title(self, user_id: str, session_id: str) -> bool:
        try:
            sessions = await self._db_session_service.list_sessions(user_id)
            for item in sessions.sessions:
                if item.session_id == session_id:
                    if SESSION_TITLE_KEY not in item.state:
                        return True
                    break
            return False
        except Exception as e:
            logger.exception(f"Failed to create session title for user {user_id} and session {session_id}: {str(e)}")
            raise

    async def run(
            self,
            user_id: str,
            session_id: str,
            request: RunAgentRequest,
            image_file: UploadFile | None = None
    ) -> RunAgentResponse:
        try:
            prompt = request.query
            if image_file is not None:
                data_uri = await self._upload_artifact(user_id=user_id, session_id=session_id, image_file=image_file)
                prompt = (
                    f"{request.query}\n\n"
                    f"{DATA_URI_PREFIX} {data_uri}\n"
                    f"{FILENAME_PREFIX} {image_file.filename}\n"
                    f"{CONTENT_TYPE} {image_file.content_type or "image/jpeg"}"
                )

            content = types.Content(role="user", parts=[types.Part(text=prompt)])
            events = self._runner.run_async(user_id=user_id, session_id=session_id, new_message=content)

            response = "No response received."
            timestamp = None
            final_seen = False

            async for event in events:
                logger.info(f"[TIMING] event author={event.author} type={type(event).__name__} at={time.time()}")
                if not final_seen and event.is_final_response():
                    final_seen = True
                    timestamp = event.timestamp
                    if event.content and event.content.parts:
                        response = event.content.parts[-1].text
                    elif event.actions and event.actions.escalate:
                        response = f"Agent escalated: {event.error_message or 'No specific message.'}"

            if await self.create_session_title(user_id, session_id):
                await self._db_session_service.create_session_title(user_id=user_id, session_id=session_id)

            logger.info(f"Run agent for session {session_id} of user {user_id} with {response}")
            return RunAgentResponse(response=response, timestamp=convert_unix_to_datetime(timestamp))
        except Exception as e:
            logger.exception(f"Failed to run agent for session {session_id} of user {user_id}: {str(e)}")
            raise
