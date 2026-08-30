import pytest
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from data_agent.routers.runner import get_agent_runner, router
from data_agent.schemas import (
    CreateSessionResponse, CreateSessionTitleResponse, ListSessionsResponse,
    LoadSessionArtifactResponse, RunAgentResponse, SessionInfo,
)

TIMESTAMP = datetime(2026, 8, 27, 10, 15, tzinfo=timezone.utc)


def _session_info(session_id="session-1"):
    return SessionInfo(
        session_id=session_id,
        app_name="data_agent",
        user_id="user-1",
        state={"session_title": "Greetings"},
        events=[],
        last_update_time=TIMESTAMP
    )


class TestRunnerRoutes:
    @pytest.fixture
    def agent_runner(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def client(self, agent_runner):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_agent_runner] = lambda: agent_runner
        return TestClient(app)

    def test_get_agent_runner(self, mocker):
        request = mocker.MagicMock()
        runner = mocker.MagicMock()
        request.app.state.agent_runner = runner

        assert get_agent_runner(request) is runner

    def test_list_sessions(self, mocker, client, agent_runner):
        agent_runner.list_sessions = mocker.AsyncMock(return_value=ListSessionsResponse(sessions=[_session_info()]))

        response = client.get("/apps/users/user-1/sessions")

        assert response.status_code == status.HTTP_200_OK
        assert [session["session_id"] for session in response.json()["sessions"]] == ["session-1"]
        assert agent_runner.list_sessions.await_args.kwargs["user_id"] == "user-1"

        agent_runner.list_sessions = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.get("/apps/users/user-1/sessions")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_create_session(self, mocker, client, agent_runner):
        agent_runner.create_session = mocker.AsyncMock(return_value=CreateSessionResponse(session_id="session-1"))

        response = client.post("/apps/users/user-1/sessions")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"session_id": "session-1"}
        assert agent_runner.create_session.await_args.kwargs["user_id"] == "user-1"

        agent_runner.create_session = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        assert client.post("/apps/users/user-1/sessions").status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_create_session_title(self, mocker, client, agent_runner):
        agent_runner.create_session_title = mocker.AsyncMock(
            return_value=CreateSessionTitleResponse(session_title="Greetings")
        )

        response = client.post("/apps/users/user-1/sessions/session-1/title")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"session_title": "Greetings"}
        assert agent_runner.create_session_title.await_args.args == ("user-1", "session-1")

        agent_runner.create_session_title = mocker.AsyncMock(side_effect=ValueError("Invalid session"))
        response = client.post("/apps/users/user-1/sessions/session-1/title")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid session"

        agent_runner.create_session_title = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        assert client.post("/apps/users/user-1/sessions/session-1/title").status_code == \
               status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_rename_session_title(self, mocker, client, agent_runner):
        agent_runner.rename_session_title = mocker.AsyncMock()

        response = client.patch("/apps/users/user-1/sessions/session-1/title?session_title=Inquiry")

        assert response.status_code == status.HTTP_200_OK
        assert agent_runner.rename_session_title.await_args.args[2].session_title == "Inquiry"

        assert client.patch("/apps/users/user-1/sessions/session-1/title").status_code == \
               status.HTTP_422_UNPROCESSABLE_CONTENT

        agent_runner.rename_session_title = mocker.AsyncMock(side_effect=ValueError("Invalid session"))
        response = client.patch("/apps/users/user-1/sessions/session-1/title?session_title=Inquiry")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        agent_runner.rename_session_title = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.patch("/apps/users/user-1/sessions/session-1/title?session_title=Inquiry")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_get_session(self, mocker, client, agent_runner):
        agent_runner.get_session = mocker.AsyncMock(return_value=_session_info())

        response = client.get("/apps/users/user-1/sessions/session-1")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["session_id"] == "session-1"
        assert agent_runner.get_session.await_args.kwargs["session_id"] == "session-1"

        agent_runner.get_session = mocker.AsyncMock(side_effect=ValueError("Invalid session"))
        assert client.get("/apps/users/user-1/sessions/session-1").status_code == status.HTTP_400_BAD_REQUEST

        agent_runner.get_session = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        assert client.get("/apps/users/user-1/sessions/session-1").status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_delete_session(self, mocker, client, agent_runner):
        agent_runner.delete_session = mocker.AsyncMock()

        response = client.delete("/apps/users/user-1/sessions/session-1")

        assert response.status_code == status.HTTP_200_OK
        assert agent_runner.delete_session.await_args.kwargs["session_id"] == "session-1"

        agent_runner.delete_session = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        assert client.delete("/apps/users/user-1/sessions/session-1").status_code == \
               status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_load_session_artifact(self, mocker, client, agent_runner):
        agent_runner.load_session_artifact = mocker.AsyncMock(
            return_value=LoadSessionArtifactResponse(content=b"image bytes", media_type="image/png")
        )

        response = client.get(
            "/apps/users/user-1/sessions/session-1/artifact?data_uri=data_agent%2Fuser-1%2Fsession-1%2Fchart.png%2F0"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.content == b"image bytes"
        assert response.headers["content-type"] == "image/png"
        assert agent_runner.load_session_artifact.await_args.kwargs["session_id"] == "session-1"
        assert agent_runner.load_session_artifact.await_args.kwargs["request"].data_uri == \
               "data_agent/user-1/session-1/chart.png/0"

        assert client.get("/apps/users/user-1/sessions/session-1/artifact").status_code == \
               status.HTTP_422_UNPROCESSABLE_CONTENT

        agent_runner.load_session_artifact = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.get("/apps/users/user-1/sessions/session-1/artifact?data_uri=missing")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_run(self, mocker, client, agent_runner):
        agent_runner.run = mocker.AsyncMock(
            return_value=RunAgentResponse(response="42 models", timestamp=TIMESTAMP)
        )

        response = client.post("/apps/users/user-1/sessions/session-1/run?query=How%20many%20models%3F")

        assert response.status_code == 200
        assert response.json()["response"] == "42 models"
        assert agent_runner.run.await_args.kwargs["request"].query == "How many models?"
        assert agent_runner.run.await_args.kwargs["request"].new_session is False
        assert agent_runner.run.await_args.kwargs["image_file"] is None

        response = client.post(
            "/apps/users/user-1/sessions/session-1/run?query=What%20is%20this%3F&new_session=true",
            files={"image_file": ("chart.png", b"image bytes", "image/png")}
        )
        assert response.status_code == status.HTTP_200_OK
        assert agent_runner.run.await_args.kwargs["request"].new_session is True
        assert agent_runner.run.await_args.kwargs["image_file"].filename == "chart.png"

        assert client.post("/apps/users/user-1/sessions/session-1/run").status_code == \
            status.HTTP_422_UNPROCESSABLE_CONTENT

        agent_runner.run = mocker.AsyncMock(side_effect=Exception("Runtime error"))
        response = client.post("/apps/users/user-1/sessions/session-1/run?query=How%20many%20models%3F")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
