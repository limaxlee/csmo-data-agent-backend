import uuid
import logging
from fastapi import UploadFile
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, Session
from google.genai import types

from common.constants import SessionStateFields, ArtifactPrefix, EventAuthors, AppNames, RunState, CONTENT_TYPE
from common.exceptions import SessionBusyError
from data_agent.schemas import *
from data_agent.agents.plugins import TimingLoggerPlugin
from data_agent.infra import ObjectStorageArtifactService, SessionLockRepository
from data_agent.services.title_generator import TitleGenerator
from data_agent.utils import convert_unix_to_datetime

logger = logging.getLogger(__name__)


class AgentRunner:
    def __init__(
            self,
            agent: BaseAgent,
            session_service: BaseSessionService,
            artifact_service: ObjectStorageArtifactService,
            title_generator: TitleGenerator,
            lock_repository: SessionLockRepository
    ):
        self._app_name = AppNames.ROOT
        self._session_service = session_service
        self._artifact_service = artifact_service
        self._title_generator = title_generator
        self._lock_repository = lock_repository
        self._runner = Runner(
            agent=agent,
            app_name=AppNames.ROOT,
            session_service=self._session_service,
            artifact_service=artifact_service,
            plugins=[TimingLoggerPlugin()]
        )

    @staticmethod
    def _find_last_user_message(session: Session) -> str | None:
        for event in reversed(session.events):
            if event.author != EventAuthors.USER or not event.content or not event.content.parts:
                continue

            for part in reversed(event.content.parts):
                if part.text and part.text.strip():
                    return part.text

        return None

    async def _ensure_not_running(self, user_id: str, session_id: str):
        """Reject session writes while a run is in progress.

        ADK rejects an append from a stale session object, so a title write
        landing between two run events would either fail itself or make the
        run's next append fail. Refusing up front keeps the run safe.
        """
        run_state = await self._lock_repository.get_run_state(
            app_name=self._app_name,
            user_id=user_id,
            session_id=session_id
        )
        if run_state == RunState.RUNNING:
            raise SessionBusyError(f"Session {session_id} has a run in progress")

    async def _set_title(self, session: Session, session_title: str):
        await self._session_service.append_event(session, Event(
            author=EventAuthors.SYSTEM,
            actions=EventActions(state_delta={SessionStateFields.TITLE: session_title})
        ))

    async def _upload_artifact(self, user_id: str, session_id: str, image_file: UploadFile) -> str:
        filename = image_file.filename
        try:
            image_bytes = await image_file.read()
            content_type = image_file.content_type or CONTENT_TYPE

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

            session_ids = [session.id for session in result.sessions]
            run_states = await self._lock_repository.get_run_states(
                app_name=self._app_name,
                user_id=user_id,
                session_ids=session_ids
            )

            sessions = []
            for session in result.sessions:
                sessions.append(
                    SessionInfo(
                        session_id=session.id,
                        app_name=session.app_name,
                        user_id=session.user_id,
                        state=session.state,
                        events=session.events,
                        last_update_time=convert_unix_to_datetime(session.last_update_time),
                        run_state=run_states.get(session.id, RunState.IDLE)
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
        """Router-facing entry point: refuses while a run holds the session."""
        await self._ensure_not_running(user_id=user_id, session_id=session_id)
        return await self._create_session_title(user_id=user_id, session_id=session_id, user_message=user_message)

    async def _create_session_title(
            self,
            user_id: str,
            session_id: str,
            user_message: str | None = None
    ) -> CreateSessionTitleResponse:
        """Does the work without the busy check, so run() can call it while holding the lock."""
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

            session_title = await self._title_generator.generate(
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
        await self._ensure_not_running(user_id=user_id, session_id=session_id)
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

            run_state = await self._lock_repository.get_run_state(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )

            logger.info(f"Retrieved {session_id} session info of user {user_id}")
            return SessionInfo(
                session_id=session.id,
                app_name=session.app_name,
                user_id=session.user_id,
                state=session.state,
                events=session.events,
                last_update_time=convert_unix_to_datetime(session.last_update_time),
                run_state=run_state
            )
        except Exception as e:
            logger.exception(f"Failed to get session {session_id} of user {user_id}: {str(e)}")
            raise

    async def get_session_run_state(self, user_id: str, session_id: str) -> RunState:
        """Lightweight state check for the frontend — no events loaded."""
        return await self._lock_repository.get_run_state(
            app_name=self._app_name,
            user_id=user_id,
            session_id=session_id
        )

    async def delete_session(self, user_id: str, session_id: str):
        try:
            # Artifacts first: if this fails the session survives and the
            # client can retry. The other order would orphan the objects.
            deleted = await self._artifact_service.delete_session_artifacts(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )
            await self._session_service.delete_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )
            await self._lock_repository.delete(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )

            logger.info(f"Deleted {session_id} session of user {user_id} with {deleted} artifact objects")
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
            artifact = await self._artifact_service.load_artifact(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id,
                filename=request.filename,
                version=self._artifact_service.parse_version(data_uri)
            )
            if not artifact or not artifact.inline_data:
                raise ValueError(f"No data found with key {data_uri} for session {session_id} of user {user_id}")

            return LoadSessionArtifactResponse(
                content=artifact.inline_data.data,
                media_type=artifact.inline_data.mime_type or request.media_type
            )
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
        # Fail fast with SessionBusyError if a run is already in progress for
        # this session. Raised BEFORE the try/finally below, so a rejected
        # request does not release someone else's lock or trigger title creation.
        if not await self._lock_repository.try_acquire(self._app_name, user_id, session_id):
            raise SessionBusyError(f"Session {session_id} already has a run in progress")

        try:
            content = await self._build_user_content(user_id, session_id, request.query, image_file)
            text, timestamp = await self._collect_final_response(user_id, session_id, content)

            logger.info(f"Run agent for session {session_id} of user {user_id} with {text}")
            return RunAgentResponse(response=text, timestamp=convert_unix_to_datetime(timestamp))
        except Exception as e:
            logger.exception(f"Failed to run agent for session {session_id} of user {user_id}: {str(e)}")
            await self._record_run_error(user_id, session_id, e)
            raise
        finally:
            # Title creation appends an event to the session, so it must happen
            # while the lock is still held. Otherwise a second run could start
            # in between and make this session object stale.
            if request.new_session:
                try:
                    await self._create_session_title(user_id=user_id, session_id=session_id, user_message=request.query)
                except Exception:
                    # Already logged inside; a missing title must not change the run's outcome.
                    logger.warning(f"Run for session {session_id} of user {user_id} continues without a title")
            await self._lock_repository.release(self._app_name, user_id, session_id)

    async def _build_user_content(
            self,
            user_id: str,
            session_id: str,
            query: str,
            image_file: UploadFile | None
    ) -> types.Content:
        parts = []
        if image_file is not None:
            data_uri = await self._upload_artifact(user_id=user_id, session_id=session_id, image_file=image_file)
            parts.append(types.Part(
                text=f"Uploaded Artifact:\n"
                     f"{ArtifactPrefix.FILENAME}: {image_file.filename}\n"
                     f"{ArtifactPrefix.DATA_URI}: {data_uri}\n"
                     f"{ArtifactPrefix.CONTENT_TYPE}: {image_file.content_type}"
            ))

        parts.append(types.Part(text=query))
        return types.Content(role=EventAuthors.USER, parts=parts)

    async def _collect_final_response(self, user_id: str, session_id: str, content: types.Content) -> tuple[str, float]:
        """Stream the run until its first final event and return (text, timestamp)."""
        events = self._runner.run_async(user_id=user_id, session_id=session_id, new_message=content)
        try:
            async for event in events:
                if not event.is_final_response():
                    continue

                if event.content and event.content.parts:
                    return event.content.parts[-1].text, event.timestamp
                if event.actions and event.actions.escalate:
                    return f"Agent escalated: {event.error_message or 'No specific message.'}", event.timestamp
                return "", event.timestamp
        finally:
            # Returning early or timing out leaves the generator suspended. Close it
            # now so ADK releases its model stream and MCP sessions deterministically.
            await events.aclose()

        raise RuntimeError(f"Agent produced no final response for session {session_id} of user {user_id}")

    async def _record_run_error(self, user_id: str, session_id: str, error: Exception):
        """Append the failure to the session. Never raises: a failed write must not replace the run's own error."""
        try:
            session = await self._session_service.get_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )
            if session:
                await self._session_service.append_event(session, Event(
                    author=EventAuthors.SYSTEM,
                    error_code="LLM_ERROR",
                    error_message=str(error)
                ))
        except Exception as e:
            logger.exception(f"Failed to record run error for session {session_id} of user {user_id}: {str(e)}")
