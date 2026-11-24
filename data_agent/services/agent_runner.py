import re
import uuid
import time
import json
import logging
from typing import Any
from fastapi import UploadFile
from google.genai import types
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, Session

from common.constants import (
    AppNames, RunState, EventAuthors,
    SessionStateFields, ArtifactPrefix, DEFAULT_AGENT_RESPONSE
)
from data_agent.infra import ObjectStorageArtifactService, SessionLockRepository, SessionRepository
from data_agent.schemas import *
from data_agent.services.title_generator import TitleGenerator
from data_agent.utils import convert_unix_to_datetime, normalize_text_filter

logger = logging.getLogger(__name__)

_LINK_ID_PATTERN = re.compile(r"link-[0-9a-f]{10}")


class AgentRunner:
    def __init__(
            self,
            agent: BaseAgent,
            session_service: BaseSessionService,
            artifact_service: ObjectStorageArtifactService,
            title_generator: TitleGenerator,
            session_lock: SessionLockRepository,
            session_repository: SessionRepository
    ):
        self._app_name = AppNames.ROOT
        self._session_service = session_service
        self._artifact_service = artifact_service
        self._title_generator = title_generator
        self._session_lock = session_lock
        self._session_repository = session_repository
        self._runner = Runner(
            agent=agent,
            app_name=AppNames.ROOT,
            session_service=self._session_service,
            artifact_service=artifact_service
        )

    @staticmethod
    def _find_last_user_prompt(session: Session) -> str | None:
        for event in reversed(session.events):
            if event.author != EventAuthors.USER or not event.content or not event.content.parts:
                continue

            for part in reversed(event.content.parts):
                if part.text and part.text.strip():
                    return part.text

        return None

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

    async def list_sessions(self, user_id: str) -> ListSessionsResponse:
        try:
            result = await self._session_service.list_sessions(app_name=self._app_name, user_id=user_id)

            session_ids = [session.id for session in result.sessions]
            run_states = await self._session_lock.get_run_states(
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

    async def list_all_sessions(self, request: ListAllSessionsRequest) -> ListAllSessionsResponse:
        filters = {
            "user_id": normalize_text_filter(request.user_id),
            "search": normalize_text_filter(request.search),
            "created_from": request.created_from,
            "created_to": request.created_to,
            "updated_from": request.updated_from,
            "updated_to": request.updated_to
        }
        try:
            sessions = await self._session_repository.list_sessions(
                app_name=self._app_name,
                **filters,
                limit=request.limit,
                offset=request.offset
            )
            total = await self._session_repository.count_sessions(app_name=self._app_name, **filters)

            logger.info(f"Listed {len(sessions)} of {total} session(s) of all users")
            return ListAllSessionsResponse(
                sessions=[SessionSummaryInfo(**session) for session in sessions],
                total=total
            )
        except Exception as e:
            logger.exception(f"Failed to list sessions of all users: {str(e)}")
            raise

    async def delete_session(self, user_id: str, session_id: str):
        try:
            await self._session_service.delete_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )

            deleted = await self._artifact_service.delete_session_artifacts(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )

            await self._session_lock.delete(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )

            logger.info(f"Deleted {session_id} session of user {user_id} with {deleted} artifact objects")
        except Exception as e:
            logger.exception(f"Failed to delete session {session_id} of user {user_id}: {str(e)}")
            raise

    async def get_session(self, user_id: str, session_id: str) -> GetSessionResponse:
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

            run_state = await self._session_lock.get_run_state(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )

            logger.info(f"Retrieved {session_id} session info of user {user_id}")
            return GetSessionResponse(
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

    async def get_session_run_state(self, user_id: str, session_id: str) -> GetRunStateResponse:
        run_state = await self._session_lock.get_run_state(
            app_name=self._app_name,
            user_id=user_id,
            session_id=session_id
        )

        return GetRunStateResponse(session_id=session_id, run_state=run_state)

    async def rename_session_title(self, user_id: str, session_id: str, request: RenameSessionRequest):
        try:
            state = await self.get_session_run_state(user_id=user_id, session_id=session_id)
            if state.run_state == RunState.RUNNING:
                raise ValueError(f"Session {session_id} of user {user_id} has a run in progress")

            session = await self._session_service.get_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id
            )
            if not session:
                raise ValueError(f"User {user_id} does not have session {session_id}")

            await self._session_service.append_event(session, Event(
                author=EventAuthors.SYSTEM,
                actions=EventActions(state_delta={SessionStateFields.TITLE: request.session_title})
            ))
            logger.info(f"Renamed session {session_id} of user {user_id} to {request.session_title}")
        except Exception as e:
            logger.exception(f"Failed to rename the session {session_id} to {request.session_title}: {str(e)}")
            raise

    async def create_session_title(
            self,
            user_id: str,
            session_id: str,
            user_prompt: str | None = None
    ) -> CreateSessionTitleResponse:
        try:
            state = await self.get_session_run_state(user_id=user_id, session_id=session_id)
            if state.run_state == RunState.RUNNING:
                raise ValueError(f"Session {session_id} of user {user_id} has a run in progress")

            return await self._create_session_title(user_id=user_id, session_id=session_id, user_message=user_prompt)
        except Exception as e:
            logger.exception(f"Failed to create title for session {session_id} of user {user_id}: {e}")
            raise

    async def _create_session_title(
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

            user_message = user_message or self._find_last_user_prompt(session)
            if not user_message:
                raise ValueError(f"Cannot create session title: session {session_id} has no user message")

            session_title = await self._title_generator.generate(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message
            )

            await self._session_service.append_event(session, Event(
                author=EventAuthors.SYSTEM,
                actions=EventActions(state_delta={SessionStateFields.TITLE: session_title})
            ))
            logger.info(f"Created title {session_title} for session {session_id} of user {user_id}")
            return CreateSessionTitleResponse(session_title=session_title)
        except Exception as e:
            logger.exception(f"Failed to create title for session {session_id} of user {user_id}: {e}")
            raise

    @classmethod
    def _get_link_map(cls, item: Any, link_map: dict[str, str]):
        if isinstance(item, dict):
            found_link_map = item.get("link_map")
            if isinstance(found_link_map, dict):
                link_map.update(found_link_map)
            for value in item.values():
                cls._get_link_map(value, link_map)
        elif isinstance(item, list):
            for value in item:
                cls._get_link_map(value, link_map)
        elif isinstance(item, str) and '"link_map"' in item:
            try:
                cls._get_link_map(json.loads(item), link_map)
            except ValueError:
                pass

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

    async def _upload_artifact(self, user_id: str, session_id: str, image_file: UploadFile) -> str:
        filename = image_file.filename
        try:
            image_bytes = await image_file.read()
            content_type = image_file.content_type

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

    async def _get_agent_response(self, user_id: str, session_id: str, content: types.Content) -> tuple[str, float]:
        events = self._runner.run_async(user_id=user_id, session_id=session_id, new_message=content)
        response = DEFAULT_AGENT_RESPONSE
        timestamp = None
        final_seen = False
        link_map = {}

        try:
            async for event in events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.function_response and part.function_response.response:
                            self._get_link_map(part.function_response.response, link_map)

                if not final_seen and event.is_final_response():
                    final_seen = True
                    timestamp = event.timestamp
                    if event.content and event.content.parts:
                        response = event.content.parts[-1].text
                    elif event.actions and event.actions.escalate:
                        response = f"Agent escalated: {event.error_message or 'No specific message.'}"
        finally:
            await events.aclose()
        if response and link_map:
            response = _LINK_ID_PATTERN.sub(lambda m: link_map.get(m.group(0), m.group(0)), response)
        if timestamp is None:
            logger.warning(f"Agent produced no final response for session {session_id} of user {user_id}")
            timestamp = time.time()

        return response, timestamp

    async def _record_run_error(self, user_id: str, session_id: str, error: Exception):
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

    async def run(
            self,
            user_id: str,
            session_id: str,
            request: RunAgentRequest,
            image_file: UploadFile | None = None
    ) -> RunAgentResponse:
        try:
            if not await self._session_lock.acquire(self._app_name, user_id, session_id):
                raise ValueError(f"Session {session_id} of user {user_id} has a run in progress")

            content = await self._build_user_content(user_id, session_id, request.query, image_file)
            response, timestamp = await self._get_agent_response(user_id, session_id, content)

            logger.info(f"Run agent for session {session_id} of user {user_id} with {response}")
            return RunAgentResponse(response=response, timestamp=convert_unix_to_datetime(timestamp))
        except Exception as e:
            logger.exception(f"Failed to run agent for session {session_id} of user {user_id}: {str(e)}")
            await self._record_run_error(user_id, session_id, e)
            raise
        finally:
            await self._session_lock.release(app_name=self._app_name, user_id=user_id, session_id=session_id)
