import jwt
import logging
from typing import Any
from fastapi import status

from common.config import SETTINGS
from common.constants import (
    AuthErrorCode, SERVICE_TOKEN_TYPE, SERVICE_TOKEN_ALGORITHM, MAX_FULL_NAME_LENGTH
)
from data_agent.exceptions import AuthError
from data_agent.schemas import SsoIdentity
from data_agent.utils import normalize_user_id

logger = logging.getLogger(__name__)


class TokenVerifier:
    def __init__(self):
        self._secret = SETTINGS.auth.service_jwt_secret
        self._issuer = SETTINGS.auth.service_jwt_issuer
        self._audience = SETTINGS.auth.service_jwt_audience

    @staticmethod
    def _invalid_token(detail: str) -> AuthError:
        return AuthError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=AuthErrorCode.INVALID_TOKEN,
            detail=detail
        )

    @staticmethod
    def _get_text(value: Any, lower: bool = False, limit: int | None = None) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None

        text = value.strip()
        if lower:
            text = text.lower()

        return text[:limit] if limit else text

    def verify(self, token: str) -> SsoIdentity:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[SERVICE_TOKEN_ALGORITHM],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "sub"]}
            )
        except jwt.InvalidTokenError as e:
            logger.info(f"Rejected service token: {type(e).__name__}")
            raise self._invalid_token("Invalid service token") from e

        if claims.get("type") != SERVICE_TOKEN_TYPE:
            logger.info("Rejected service token: unexpected token type")
            raise self._invalid_token("Invalid service token")

        subject, username = claims.get("sub"), claims.get("username")
        if not isinstance(subject, str) or not isinstance(username, str):
            logger.info("Rejected service token: subject or username is missing")
            raise self._invalid_token("Invalid service identity")

        try:
            user_id = normalize_user_id(subject)
        except ValueError as e:
            logger.info("Rejected service token: subject is not a valid user id")
            raise self._invalid_token("Invalid service identity") from e

        if username.strip().casefold() != user_id:
            logger.info("Rejected service token: username does not match subject")
            raise self._invalid_token("Invalid service identity")

        return SsoIdentity(
            user_id=user_id,
            email=self._get_text(claims.get("email"), lower=True),
            full_name=self._get_text(claims.get("full_name"), limit=MAX_FULL_NAME_LENGTH),
            department=self._get_text(claims.get("department")),
            company=self._get_text(claims.get("company")),
            unique_name=self._get_text(claims.get("unique_name")),
            sid=self._get_text(claims.get("sid")),
            roles=[role for role in claims.get("roles") or [] if isinstance(role, str)],
            claims=claims
        )
