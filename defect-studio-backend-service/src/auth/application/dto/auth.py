"""Auth DTOs — Input/Output dataclasses for auth use cases."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AuthOutput:
    access_token: str
    refresh_token: str
    user_id: uuid.UUID
    user_email: str
    user_name: str | None
    user_role: str
    user_created_at: datetime | None = None


@dataclass
class RegisterInput:
    email: str
    password: str
    name: str | None = None


@dataclass
class LoginInput:
    email: str
    password: str


@dataclass
class RefreshTokenInput:
    refresh_token: str