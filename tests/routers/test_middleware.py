import re
import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from data_agent.routers import log_requests_middleware


class TestLogRequestsMiddleware:
    def _build_client(self):
        app = FastAPI()
        app.middleware("http")(log_requests_middleware)

        @app.get("/ping")
        async def ping():
            return {"status": "ok"}

        return TestClient(app)

    def test_logs_request_and_response(self, caplog):
        client = self._build_client()

        with caplog.at_level(logging.INFO, logger="data_agent.routers"):
            response = client.get("/ping?user=user-1")

        assert response.status_code == status.HTTP_200_OK

        messages = [record.getMessage() for record in caplog.records]
        assert "Request: GET /ping?user=user-1" in messages
        assert any(re.fullmatch(r"Response: GET /ping - 200 \(\d+\.\d{2}ms\)", m) for m in messages)

    def test_logs_error_response_status(self, caplog):
        client = self._build_client()

        with caplog.at_level(logging.INFO, logger="data_agent.routers"):
            response = client.get("/missing")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        messages = [record.getMessage() for record in caplog.records]
        assert any(m.startswith("Response: GET /missing - 404") for m in messages)
