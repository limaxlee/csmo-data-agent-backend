"""Auth DTOs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from src.auth.application.dto import (
    AuthOutput,
    LoginInput,
    RefreshTokenInput,
    RegisterInput,
)
from src.common.domain.time import utc_now


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str | None = Field(None, max_length=100)

    def to_input(self) -> RegisterInput:
        return RegisterInput(email=self.email, password=self.password, name=self.name)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    def to_input(self) -> LoginInput:
        return LoginInput(email=self.email, password=self.password)


class SsoLinkRequest(BaseModel):
    service_token: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str

    def to_input(self) -> RefreshTokenInput:
        return RefreshTokenInput(refresh_token=self.refresh_token)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

    @classmethod
    def from_output(cls, output: AuthOutput) -> TokenResponse:
        return cls(
            access_token=output.access_token,
            refresh_token=output.refresh_token,
            user=UserResponse(
                id=output.user_id,
                email=output.user_email,
                name=output.user_name,
                role=output.user_role,
                created_at=output.user_created_at or utc_now(),
            ),
        )
