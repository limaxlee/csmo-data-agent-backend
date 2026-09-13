from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .logging import log_requests_middleware


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(log_requests_middleware)
