"""Verify central web-auth service JWTs before trusting any identity claims."""

from __future__ import annotations

from jose import JWTError, jwt

from src.auth.application.dto.sso import SsoIdentity, normalize_email
from src.auth.domain.exceptions import InvalidToken
from src.container.settings import Settings, get_settings


class ServiceTokenVerifier:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def verify(self, token: str) -> SsoIdentity:
        if not self._settings.service_jwt_secret:
            raise InvalidToken("SSO is unavailable")
        try:
            claims = jwt.decode(
                token,
                self._settings.service_jwt_secret,
                algorithms=["HS256"],
                issuer="web-auth",
                audience="dice-backend",
                options={"require_exp": True, "require_sub": True},
            )
        except JWTError as exc:
            raise InvalidToken("Invalid service token") from exc

        if claims.get("type") != "service":
            raise InvalidToken("Invalid service token")
        subject = claims.get("sub")
        username = claims.get("username")
        if not isinstance(subject, str) or not isinstance(username, str):
            raise InvalidToken("Invalid service identity")
        loginid = subject.strip().casefold()
        if (
            not loginid
            or len(loginid) > 255
            or any(ch.isspace() or ord(ch) < 32 for ch in loginid)
            or loginid in {"undefined", "null", "none"}
            or username.strip().casefold() != loginid
        ):
            raise InvalidToken("Invalid service identity")

        name = claims.get("full_name")
        if not isinstance(name, str) or not name.strip():
            name = None
        else:
            name = name.strip()[:100]
        return SsoIdentity(
            loginid=loginid,
            email=normalize_email(claims.get("email")),
            name=name,
        )
