import uuid
import logging
from google.adk.events import Event, EventActions
from google.adk.sessions import BaseSessionService, DatabaseSessionService, Session

from common.config import SETTINGS
from common.constants import ROOT_APP_NAME, USER_AUTHOR, SYSTEM_AUTHOR, SESSION_TITLE_KEY
from data_agent.schemas import (
    SessionInfo, ListSessionsResponse, CreateSessionResponse, RenameSessionRequest,
    CreateSessionTitleResponse
)
from data_agent.services.system_runner import SystemAgentRunner
# from data_agent.storage import ObjectStorage
from data_agent.utils import convert_unix_to_datetime

logger = logging.getLogger(__name__)


def create_session_store() -> DatabaseSessionService:
    db_url = f"{SETTINGS.postgresql_db.host}:{SETTINGS.postgresql_db.port}/{SETTINGS.postgresql_db.name}"
    return DatabaseSessionService(db_url=f"postgresql+asyncpg://postgres@{db_url}")


class PostgreSQLSessionService:
    def __init__(
            self,
            session_service: BaseSessionService,
            system_runner: SystemAgentRunner,
            # object_storage: ObjectStorage
    ):
        # self._storage = object_storage
        self._session_service = session_service
        self._system_runner = system_runner
        self._app_name = ROOT_APP_NAME

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

    async def create_session_title(self, user_id: str, session_id: str) -> CreateSessionTitleResponse:
        try:
            session = await self._session_service.get_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )
            if not session:
                raise ValueError(f"User {user_id} does not have session {session_id}")

            user_message = self._find_last_user_message(session)
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

    # async def load_session_artifact(
    #         self,
    #         user_id: str,
    #         session_id: str,
    #         request: LoadSessionArtifactRequest
    # ) -> LoadSessionArtifactResponse:
    #     data_uri = request.data_uri
    #     try:
    #         data_info = await self._storage.retrieve_object_info(key=data_uri)
    #         media_type = data_info.get("ContentType") or "application/octet-stream"
    #
    #         data_object = await self._storage.retrieve_object(data_uri)
    #         if not data_object:
    #             raise ValueError(f"No data found with key {data_uri} for session {session_id} of user {user_id}")
    #
    #         return LoadSessionArtifactResponse(content=data_object, media_type=media_type)
    #     except Exception as e:
    #         logger.exception(f"Failed to load artifact {data_uri} for session {session_id} of user {user_id}: {str(e)}")
    #         raise

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
