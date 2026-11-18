"""Exception handlers — map domain exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.auth.domain.exceptions import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidToken,
    PasswordRegistrationDisabled,
    SsoAccountConflict,
    SsoAccountUnlinked,
    SsoEmailMismatch,
    UserNotFound,
)
from src.common.domain.exceptions import (
    DomainException,
    StorageError,
)
from src.plan.domain.exceptions import PlanNotFound
from src.result.domain.exceptions import ArtifactNotFound
from src.run.domain.exceptions import (
    AgentServiceError,
    RunNotAwaitingInput,
    RunNotFound,
)
from src.thread.domain.exceptions import ThreadDeletionConflict, ThreadNotFound
from src.train_data.domain.exceptions import (
    FileNotFound,
    InvalidCategory,
    InvalidFileType,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the FastAPI app."""

    @app.exception_handler(EmailAlreadyRegistered)
    async def _email_already_registered(_req: Request, exc: EmailAlreadyRegistered):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(InvalidCredentials)
    async def _invalid_credentials(_req: Request, exc: InvalidCredentials):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(InvalidToken)
    async def _invalid_token(_req: Request, exc: InvalidToken):
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(SsoAccountUnlinked)
    async def _sso_unlinked(_req: Request, exc: SsoAccountUnlinked):
        return JSONResponse(
            status_code=409, content={"detail": str(exc), "code": "sso_account_unlinked"}
        )

    @app.exception_handler(SsoAccountConflict)
    async def _sso_conflict(_req: Request, exc: SsoAccountConflict):
        return JSONResponse(
            status_code=409, content={"detail": str(exc), "code": "sso_account_conflict"}
        )

    @app.exception_handler(SsoEmailMismatch)
    async def _sso_email_mismatch(_req: Request, exc: SsoEmailMismatch):
        return JSONResponse(
            status_code=409, content={"detail": str(exc), "code": "sso_email_mismatch"}
        )

    @app.exception_handler(PasswordRegistrationDisabled)
    async def _registration_disabled(_req: Request, exc: PasswordRegistrationDisabled):
        return JSONResponse(
            status_code=403, content={"detail": str(exc), "code": "registration_disabled"}
        )

    @app.exception_handler(UserNotFound)
    async def _user_not_found(_req: Request, exc: UserNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ThreadNotFound)
    async def _thread_not_found(_req: Request, exc: ThreadNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ThreadDeletionConflict)
    async def _thread_deletion_conflict(_req: Request, exc: ThreadDeletionConflict):
        return JSONResponse(status_code=409, content={"detail": str(exc), "code": exc.code})

    @app.exception_handler(RunNotFound)
    async def _run_not_found(_req: Request, exc: RunNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(PlanNotFound)
    async def _plan_not_found(_req: Request, exc: PlanNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(FileNotFound)
    async def _file_not_found(_req: Request, exc: FileNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ArtifactNotFound)
    async def _artifact_not_found(_req: Request, exc: ArtifactNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidCategory)
    async def _invalid_category(_req: Request, exc: InvalidCategory):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(InvalidFileType)
    async def _invalid_file_type(_req: Request, exc: InvalidFileType):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(RunNotAwaitingInput)
    async def _run_not_awaiting_input(_req: Request, exc: RunNotAwaitingInput):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(AgentServiceError)
    async def _agent_service_error(_req: Request, exc: AgentServiceError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(StorageError)
    async def _storage_error(_req: Request, exc: StorageError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(DomainException)
    async def _generic_domain(_req: Request, exc: DomainException):
        return JSONResponse(status_code=400, content={"detail": str(exc)})
