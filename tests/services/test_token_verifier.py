import jwt
import time
import pytest
from starlette import status

from common.config import SETTINGS
from common.constants import AuthErrorCode, MAX_USER_ID_LENGTH, MAX_FULL_NAME_LENGTH
from data_agent.exceptions import AuthError
from data_agent.services.token_verifier import TokenVerifier


def _claims(**overrides):
    now = int(time.time())
    claims = {
        "sub": "User.One",
        "username": "user.one",
        "email": "User.One@Samsung.com",
        "full_name": "user.one@samsung.com",
        "department": "Test Dept",
        "company": "Test Co",
        "unique_name": "CORP\\user.one",
        "sid": "S-1-5-21-1",
        "roles": ["group-a", 7, "group-b"],
        "type": "service",
        "iss": "web-auth",
        "aud": "dice-backend",
        "iat": now,
        "exp": now + 3600
    }
    claims.update(overrides)
    return {key: value for key, value in claims.items() if value is not ...}


def _token(secret=None, algorithm="HS256", **overrides):
    return jwt.encode(_claims(**overrides), secret or SETTINGS.auth.service_jwt_secret, algorithm=algorithm)


class TestTokenVerifier:
    @pytest.fixture
    def verifier(self):
        return TokenVerifier()

    def test_settings(self, verifier):
        assert verifier._secret == SETTINGS.auth.service_jwt_secret
        assert verifier._issuer == "web-auth"
        assert verifier._audience == "dice-backend"

    def test_verify(self, verifier):
        identity = verifier.verify(_token())

        assert identity.user_id == "user.one"
        assert identity.email == "user.one@samsung.com"
        assert identity.full_name == "user.one@samsung.com"
        assert identity.department == "Test Dept"
        assert identity.company == "Test Co"
        assert identity.unique_name == "CORP\\user.one"
        assert identity.sid == "S-1-5-21-1"
        assert identity.roles == ["group-a", "group-b"]
        assert identity.claims["sub"] == "User.One"
        assert identity.claims["iss"] == "web-auth"

    def test_verify_optional_claims(self, verifier):
        identity = verifier.verify(_token(
            email=None,
            full_name="  ",
            department=...,
            company=7,
            unique_name=None,
            sid=None,
            roles=None
        ))

        assert identity.user_id == "user.one"
        assert identity.email is None
        assert identity.full_name is None
        assert identity.department is None
        assert identity.company is None
        assert identity.unique_name is None
        assert identity.sid is None
        assert identity.roles == []

        identity = verifier.verify(_token(full_name="n" * (MAX_FULL_NAME_LENGTH + 10)))

        assert identity.full_name == "n" * MAX_FULL_NAME_LENGTH

    @pytest.mark.parametrize("overrides", [
        {"exp": int(time.time()) - 60},
        {"exp": ...},
        {"sub": ...},
        {"iss": "platform"},
        {"iss": ...},
        {"aud": "labeler"},
        {"aud": ...},
        {"type": "access"},
        {"type": ...},
        {"username": "another.user"},
        {"username": ...},
        {"username": 7},
        {"sub": "null", "username": "null"},
        {"sub": "undefined", "username": "undefined"},
        {"sub": "  ", "username": "  "},
        {"sub": "user one", "username": "user one"},
        {"sub": "team/user", "username": "team/user"},
        {"sub": "CORP\\user", "username": "CORP\\user"},
        {"sub": "u" * (MAX_USER_ID_LENGTH + 1), "username": "u" * (MAX_USER_ID_LENGTH + 1)}
    ])
    def test_verify_rejects_invalid_claims(self, verifier, overrides):
        with pytest.raises(AuthError) as error:
            verifier.verify(_token(**overrides))

        assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.value.code == AuthErrorCode.INVALID_TOKEN

    def test_verify_rejects_invalid_signature(self, verifier):
        tokens = [
            _token(secret="another-service-jwt-secret-for-unit-tests"),
            _token(algorithm="HS512"),
            jwt.encode(_claims(), None, algorithm="none"),
            "not-a-token",
            ""
        ]

        for token in tokens:
            with pytest.raises(AuthError) as error:
                verifier.verify(token)

            assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert error.value.code == AuthErrorCode.INVALID_TOKEN
            assert error.value.detail == "Invalid service token"
