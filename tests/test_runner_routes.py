from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from data_agent.routers.runner import get_agent_runner, router
from data_agent.schemas import (
    CreateSessionResponse,
    CreateSessionTitleResponse,
    ListSessionsResponse,
    RunAgentResponse,
    SessionInfo,
)

TIMESTAMP = datetime(2026, 8, 27, 10, 15, tzinfo=timezone.utc)


def _session_info(session_id="session-1"):
    return SessionInfo(
        session_id=session_id,
        app_name="data_agent",
        user_id="user-1",
        state={"session_title": "Monthly sales"},
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
        agent_runner.list_sessions = mocker.AsyncMock(
            return_value=ListSessionsResponse(sessions=[_session_info()])
        )

        response = client.get("/apps/users/user-1/sessions")

        assert response.status_code == 200
        assert [s["session_id"] for s in response.json()["sessions"]] == ["session-1"]
        assert agent_runner.list_sessions.await_args.kwargs["user_id"] == "user-1"

        agent_runner.list_sessions = mocker.AsyncMock(side_effect=Exception("boom"))
        response = client.get("/apps/users/user-1/sessions")
        assert response.status_code == 500
        assert response.json()["detail"] == "boom"

    def test_create_session(self, mocker, client, agent_runner):
        agent_runner.create_session = mocker.AsyncMock(
            return_value=CreateSessionResponse(session_id="session-1")
        )

        response = client.post("/apps/users/user-1/sessions")

        assert response.status_code == 200
        assert response.json() == {"session_id": "session-1"}
        assert agent_runner.create_session.await_args.kwargs["user_id"] == "user-1"

        agent_runner.create_session = mocker.AsyncMock(side_effect=Exception("boom"))
        assert client.post("/apps/users/user-1/sessions").status_code == 500

    def test_create_session_title(self, mocker, client, agent_runner):
        agent_runner.create_session_title = mocker.AsyncMock(
            return_value=CreateSessionTitleResponse(session_title="Monthly sales")
        )

        response = client.post("/apps/users/user-1/sessions/session-1/title")

        assert response.status_code == 200
        assert response.json() == {"session_title": "Monthly sales"}
        assert agent_runner.create_session_title.await_args.args == ("user-1", "session-1")

        # A missing session is a client error, anything else is a server error.
        agent_runner.create_session_title = mocker.AsyncMock(side_effect=ValueError("no such session"))
        response = client.post("/apps/users/user-1/sessions/session-1/title")
        assert response.status_code == 400
        assert response.json()["detail"] == "no such session"

        agent_runner.create_session_title = mocker.AsyncMock(side_effect=Exception("boom"))
        assert client.post("/apps/users/user-1/sessions/session-1/title").status_code == 500

    def test_rename_session_title(self, mocker, client, agent_runner):
        agent_runner.rename_session_title = mocker.AsyncMock()

        response = client.patch("/apps/users/user-1/sessions/session-1/title?session_title=Renamed")

        assert response.status_code == 200
        # The title arrives as a query parameter, not a JSON body.
        assert agent_runner.rename_session_title.await_args.args[2].session_title == "Renamed"

        # The parameter is required.
        assert client.patch("/apps/users/user-1/sessions/session-1/title").status_code == 422

        agent_runner.rename_session_title = mocker.AsyncMock(side_effect=ValueError("no such session"))
        response = client.patch("/apps/users/user-1/sessions/session-1/title?session_title=Renamed")
        assert response.status_code == 400

        agent_runner.rename_session_title = mocker.AsyncMock(side_effect=Exception("boom"))
        response = client.patch("/apps/users/user-1/sessions/session-1/title?session_title=Renamed")
        assert response.status_code == 500

    def test_get_session(self, mocker, client, agent_runner):
        agent_runner.get_session = mocker.AsyncMock(return_value=_session_info())

        response = client.get("/apps/users/user-1/sessions/session-1")

        assert response.status_code == 200
        assert response.json()["session_id"] == "session-1"
        assert agent_runner.get_session.await_args.kwargs["session_id"] == "session-1"

        agent_runner.get_session = mocker.AsyncMock(side_effect=ValueError("no such session"))
        assert client.get("/apps/users/user-1/sessions/session-1").status_code == 400

        agent_runner.get_session = mocker.AsyncMock(side_effect=Exception("boom"))
        assert client.get("/apps/users/user-1/sessions/session-1").status_code == 500

    def test_delete_session(self, mocker, client, agent_runner):
        agent_runner.delete_session = mocker.AsyncMock()

        response = client.delete("/apps/users/user-1/sessions/session-1")

        assert response.status_code == 200
        assert agent_runner.delete_session.await_args.kwargs["session_id"] == "session-1"

        agent_runner.delete_session = mocker.AsyncMock(side_effect=Exception("boom"))
        assert client.delete("/apps/users/user-1/sessions/session-1").status_code == 500

    def test_run(self, mocker, client, agent_runner):
        agent_runner.run = mocker.AsyncMock(
            return_value=RunAgentResponse(response="42 orders", timestamp=TIMESTAMP)
        )

        response = client.post("/apps/users/user-1/sessions/session-1/run?query=How%20many%20orders%3F")

        assert response.status_code == 200
        assert response.json()["response"] == "42 orders"
        assert agent_runner.run.await_args.kwargs["request"].query == "How many orders?"
        assert agent_runner.run.await_args.kwargs["request"].new_session is False
        assert agent_runner.run.await_args.kwargs["image_file"] is None

        # Text fields ride on the query string, the body carries the optional upload.
        response = client.post(
            "/apps/users/user-1/sessions/session-1/run?query=What%20is%20this%3F&new_session=true",
            files={"image_file": ("chart.png", b"image bytes", "image/png")}
        )
        assert response.status_code == 200
        assert agent_runner.run.await_args.kwargs["request"].new_session is True
        assert agent_runner.run.await_args.kwargs["image_file"].filename == "chart.png"

        # query is required.
        assert client.post("/apps/users/user-1/sessions/session-1/run").status_code == 422

        agent_runner.run = mocker.AsyncMock(side_effect=Exception("boom"))
        response = client.post("/apps/users/user-1/sessions/session-1/run?query=How%20many%20orders%3F")
        assert response.status_code == 500
        assert response.json()["detail"] == "boom"
