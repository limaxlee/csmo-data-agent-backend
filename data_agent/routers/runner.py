import time
import logging
from typing import Annotated
from fastapi import APIRouter, status, HTTPException, Path, Depends, Request, UploadFile, File, Response

from data_agent.runners import RootAgentRunner
from data_agent.schemas import *

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apps", tags=["runner"])


def get_agent_runner(request: Request) -> RootAgentRunner:
    return request.app.state.agent_runner


AgentRunner = Annotated[RootAgentRunner, Depends(get_agent_runner)]


@router.get(
    "/users/{user_id}/sessions",
    response_model=ListSessionsResponse,
    status_code=status.HTTP_200_OK
)
async def list_sessions(
        user_id: Annotated[str, Path()],
        agent_runner: AgentRunner
):
    try:
        return await agent_runner.list_sessions(user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/users/{user_id}/sessions",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_200_OK
)
async def create_session(
        user_id: Annotated[str, Path()],
        agent_runner: AgentRunner
):
    try:
        return await agent_runner.create_session(user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/users/{user_id}/sessions/{session_id}/title",
    response_model=CreateSessionTitleResponse,
    status_code=status.HTTP_200_OK
)
async def create_session_title(
        user_id: Annotated[str, Path()],
        session_id: Annotated[str, Path()],
        agent_runner: AgentRunner
):
    try:
        return await agent_runner.create_session_title(user_id, session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch(
    "/users/{user_id}/sessions/{session_id}/title",
    status_code=status.HTTP_200_OK
)
async def rename_session_title(
        user_id: Annotated[str, Path()],
        session_id: Annotated[str, Path()],
        request: Annotated[RenameSessionRequest, Depends()],
        agent_runner: AgentRunner
):
    try:
        await agent_runner.rename_session_title(user_id, session_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/users/{user_id}/sessions/{session_id}/artifact",
    response_class=Response,
    status_code=status.HTTP_200_OK
)
async def load_session_artifact(
        user_id: Annotated[str, Path()],
        session_id: Annotated[str, Path()],
        request: Annotated[LoadSessionArtifactRequest, Depends()],
        agent_runner: AgentRunner
):
    try:
        artifact = await agent_runner.load_session_artifact(
            user_id=user_id,
            session_id=session_id,
            request=request
        )
        return Response(content=artifact.content, media_type=artifact.media_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/users/{user_id}/sessions/{session_id}",
    response_model=SessionInfo,
    status_code=status.HTTP_200_OK
)
async def get_session(
        user_id: Annotated[str, Path()],
        session_id: Annotated[str, Path()],
        agent_runner: AgentRunner
):
    try:
        return await agent_runner.get_session(user_id=user_id, session_id=session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/users/{user_id}/sessions/{session_id}",
    status_code=status.HTTP_200_OK
)
async def delete_session(
        user_id: Annotated[str, Path()],
        session_id: Annotated[str, Path()],
        agent_runner: AgentRunner
):
    try:
        await agent_runner.delete_session(user_id=user_id, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/users/{user_id}/sessions/{session_id}/run",
    response_model=RunAgentResponse,
    status_code=status.HTTP_200_OK
)
async def run(
        user_id: Annotated[str, Path()],
        session_id: Annotated[str, Path()],
        request: Annotated[RunAgentRequest, Depends()],
        agent_runner: AgentRunner,
        image_file: UploadFile | None = File(None),
):
    t0 = time.monotonic()
    logger.info(f"[TIMING] /run API START session={session_id} query={request.query!r}")
    try:
        result = await agent_runner.run(
            user_id=user_id,
            session_id=session_id,
            request=request,
            image_file=image_file
        )
        logger.info(f"[TIMING] /run API END session={session_id} elapsed={time.monotonic() - t0:.2f}s")
        return result
    except Exception as e:
        logger.info(f"[TIMING] /run FAILED session={session_id} elapsed={time.monotonic() - t0:.2f}s")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
