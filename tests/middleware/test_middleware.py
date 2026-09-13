import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from data_agent.middleware import register_middleware


class TestRegisterMiddleware:
    def _build_client(self):
        app = FastAPI()
        register_middleware(app)

        @app.get("/ping")
        async def ping():
            return {"status": "ok"}

        return TestClient(app)

    def test_allows_cross_origin_requests(self):
        client = self._build_client()

        response = client.options(
            "/ping",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "GET" in response.headers["access-control-allow-methods"]

        response = client.get("/ping", headers={"Origin": "http://localhost:3000"})

        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers

    def test_logs_requests(self, caplog):
        client = self._build_client()

        with caplog.at_level(logging.INFO, logger="data_agent.middleware"):
            response = client.get("/ping?user=user-1")

        assert response.status_code == status.HTTP_200_OK
        messages = [record.getMessage() for record in caplog.records]
        assert "Request: GET /ping?user=user-1" in messages
        assert any(m.startswith("Response: GET /ping - 200") for m in messages)
