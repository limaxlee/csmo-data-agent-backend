"""Auth UseCase interfaces (driving ports)."""

from __future__ import annotations

import abc

from src.auth.application.dto.auth import AuthOutput, LoginInput, RefreshTokenInput, RegisterInput


class RegisterUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: RegisterInput) -> AuthOutput: ...


class LoginUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: LoginInput) -> AuthOutput: ...


class RefreshTokenUseCase(abc.ABC):
    @abc.abstractmethod
    async def execute(self, inp: RefreshTokenInput) -> AuthOutput: ...