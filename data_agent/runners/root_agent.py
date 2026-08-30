import uuid
import logging
from fastapi import UploadFile
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService, Session
from google.genai import types

from common.config import SETTINGS
from common.constants import (
    ROOT_APP_NAME, USER_AUTHOR, SYSTEM_AUTHOR, SESSION_TITLE_KEY,
    DATA_URI_PREFIX, FILENAME_PREFIX, CONTENT_TYPE
)
from data_agent.agents import root_agent
from data_agent.schemas import (
    RunAgentRequest, RunAgentResponse, SessionInfo, ListSessionsResponse,
    CreateSessionResponse, RenameSessionRequest, CreateSessionTitleResponse,
    LoadSessionArtifactRequest, LoadSessionArtifactResponse
)
from data_agent.runners.system_agent import SystemAgentRunner
from data_agent.storage.os_artifact import OSArtifactService
from data_agent.utils import convert_unix_to_datetime

logger = logging.getLogger(__name__)


class RootAgentRunner:
    def __init__(
            self,
            artifact_service: OSArtifactService,
            system_runner: SystemAgentRunner
    ):
        self._app_name = ROOT_APP_NAME
        self._artifact_service = artifact_service
        self._system_runner = system_runner
        self._db_url = f"{SETTINGS.postgresql_db.host}:{SETTINGS.postgresql_db.port}/{SETTINGS.postgresql_db.name}"
        self._session_service = DatabaseSessionService(db_url=f"postgresql+asyncpg://postgres@{self._db_url}")

        self._runner = Runner(
            agent=root_agent,
            app_name=ROOT_APP_NAME,
            session_service=self._session_service,
            artifact_service=artifact_service
        )

    @staticmethod
    def _find_last_user_message(session: Session) -> str | None:
        for event in reversed(session.events):
            if event.author != USER_AUTHOR or not event.content or not event.content.parts:
                continue

            for part in reversed(event.content.parts):
                if part.text and part.text.strip():
                    return part.text

        return None

    async def _set_title(self, session: Session, session_title: str):
        await self._session_service.append_event(session, Event(
            author=SYSTEM_AUTHOR,
            actions=EventActions(state_delta={SESSION_TITLE_KEY: session_title})
        ))

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

    async def list_sessions(self, user_id: str) -> ListSessionsResponse:
        try:
            result = await self._session_service.list_sessions(app_name=self._app_name, user_id=user_id)

            sessions = []
            for session in result.sessions:
                sessions.append(
                    SessionInfo(
                        session_id=session.id,
                        app_name=session.app_name,
                        user_id=session.user_id,
                        state=session.state,
                        events=session.events,
                        last_update_time=convert_unix_to_datetime(session.last_update_time)
                    )
                )

            logger.info(f"Retrieved session list of user {user_id}: {[session.session_id for session in sessions]}")
            return ListSessionsResponse(sessions=sessions)
        except Exception as e:
            logger.exception(f"Failed to list sessions of user {user_id}: {str(e)}")
            raise

    async def create_session(self, user_id: str) -> CreateSessionResponse:
        try:
            session = await self._session_service.create_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=uuid.uuid4().hex
            )

            logger.info(f"Created session for user {user_id} with id: {session.id}")
            return CreateSessionResponse(session_id=session.id)
        except Exception as e:
            logger.exception(f"Failed to create new session for user {user_id}: {str(e)}")
            raise

    async def create_session_title(
            self,
            user_id: str,
            session_id: str,
            user_message: str | None = None
    ) -> CreateSessionTitleResponse:
        try:
            session = await self._session_service.get_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )
            if not session:
                raise ValueError(f"User {user_id} does not have session {session_id}")

            user_message = user_message or self._find_last_user_message(session)
            if not user_message:
                raise ValueError(f"Cannot create session title: session {session_id} has no user message")

            session_title = await self._system_runner.create_session_title(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message
            )

            await self._set_title(session, session_title)

            logger.info(f"Created a title {session_title} for session {session_id} of user {user_id}")
            return CreateSessionTitleResponse(session_title=session_title)
        except Exception as e:
            logger.exception(f"Failed to create a title for session {session_id} of user {user_id}: {str(e)}")
            raise

    async def rename_session_title(self, user_id: str, session_id: str, request: RenameSessionRequest):
        try:
            session = await self._session_service.get_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )
            if not session:
                raise ValueError(f"User {user_id} does not have session {session_id}")

            await self._set_title(session, request.session_title)

            logger.info(f"Renamed session {session_id} of user {user_id} to {request.session_title}")
        except Exception as e:
            logger.exception(f"Failed to rename the session {session_id} to {request.session_title}: {str(e)}")
            raise

    async def get_session(self, user_id: str, session_id: str) -> SessionInfo:
        try:
            session = await self._session_service.get_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )
            if not session:
                raise ValueError(f"User {user_id} does not have session {session_id}")

            for event in session.events:
                event.timestamp = convert_unix_to_datetime(event.timestamp)

            logger.info(f"Retrieved {session_id} session info of user {user_id}")
            return SessionInfo(
                session_id=session.id,
                app_name=session.app_name,
                user_id=session.user_id,
                state=session.state,
                events=session.events,
                last_update_time=convert_unix_to_datetime(session.last_update_time)
            )
        except Exception as e:
            logger.exception(f"Failed to get session {session_id} of user {user_id}: {str(e)}")
            raise

    async def delete_session(self, user_id: str, session_id: str):
        try:
            await self._session_service.delete_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )

            logger.info(f"Deleted {session_id} session of user {user_id}")
        except Exception as e:
            logger.exception(f"Failed to delete session {session_id} of user {user_id}: {str(e)}")
            raise

    async def load_session_artifact(
            self,
            user_id: str,
            session_id: str,
            request: LoadSessionArtifactRequest
    ) -> LoadSessionArtifactResponse:
        data_uri = request.data_uri
        try:
            data_info = await self._storage.retrieve_object_info(key=data_uri)
            media_type = data_info.get("ContentType") or "application/octet-stream"
    
            data_object = await self._storage.retrieve_object(data_uri)
            if not data_object:
                raise ValueError(f"No data found with key {data_uri} for session {session_id} of user {user_id}")
    
            return LoadSessionArtifactResponse(content=data_object, media_type=media_type)
        except Exception as e:
            logger.exception(f"Failed to load artifact {data_uri} for session {session_id} of user {user_id}: {str(e)}")
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
            parts = []
            if image_file is not None:
                data_uri = await self._upload_artifact(user_id=user_id, session_id=session_id, image_file=image_file)
                parts.append(types.Part(
                    text=f"Uploaded Artifact:\n"
                         f"{FILENAME_PREFIX}: {image_file.filename}\n"
                         f"{DATA_URI_PREFIX}: {data_uri}\n"
                         f"{CONTENT_TYPE}: {image_file.content_type or "image/jpeg"}"
                ))

            parts.append(types.Part(text=prompt))
            content = types.Content(role=USER_AUTHOR, parts=parts)
            events = self._runner.run_async(user_id=user_id, session_id=session_id, new_message=content)

            response = "No response received."
            timestamp = None
            final_seen = False

            async for event in events:
                if not final_seen and event.is_final_response():
                    final_seen = True
                    timestamp = event.timestamp
                    if event.content and event.content.parts:
                        response = event.content.parts[-1].text
                    elif event.actions and event.actions.escalate:
                        response = f"Agent escalated: {event.error_message or 'No specific message.'}"

            logger.info(f"Run agent for session {session_id} of user {user_id} with {response}")
            return RunAgentResponse(response=response, timestamp=convert_unix_to_datetime(timestamp))
        except Exception as e:
            logger.exception(f"Failed to run agent for session {session_id} of user {user_id}: {str(e)}")
            raise
        finally:
            if request.new_session:
                try:
                    await self.create_session_title(user_id=user_id, session_id=session_id, user_message=request.query)
                except Exception as e:
                    logger.exception(f"Failed to create a title for session {session_id} of user {user_id}: {str(e)}")
