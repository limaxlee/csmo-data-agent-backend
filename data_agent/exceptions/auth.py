from fastapi import Request, status
from fastapi.responses import JSONResponse


class AuthError(Exception):
    def __init__(self, status_code: int, code: str, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


async def handle_auth_error(request: Request, error: AuthError) -> JSONResponse:
    headers = None
    if error.status_code == status.HTTP_401_UNAUTHORIZED:
        headers = {"WWW-Authenticate": "Bearer"}

    return JSONResponse(
        status_code=error.status_code,
        content={"detail": error.detail, "code": error.code},
        headers=headers
    )
