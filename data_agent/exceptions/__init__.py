from fastapi import FastAPI

from .auth import AuthError, handle_auth_error


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AuthError, handle_auth_error)
