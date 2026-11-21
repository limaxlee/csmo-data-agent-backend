"""Security utilities for service-to-service JWT tokens.

Note: User authentication is handled by ADFS SSO (web-auth).
Password hashing and user JWT functions have been removed.
This module only contains service token functions for Platform → Labeler SSO.
"""

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings

# JWT settings for service tokens
ALGORITHM = "HS256"
SERVICE_TOKEN_EXPIRE_MINUTES = 5  # 5 minutes (short-lived for SSO)


def create_service_token(data: dict[str, Any]) -> str:
    """
    Create a service-to-service JWT token for SSO.

    Used for Platform → Labeler SSO flow. This token uses a separate
    SERVICE_JWT_SECRET and has a short expiration (5 minutes) for security.

    Args:
        data: Data to encode in the token (user_id, email, etc.)

    Returns:
        Encoded JWT service token

    Example:
        >>> token = create_service_token({
        ...     "user_id": "550e8400-e29b-41d4-a716-446655440000",  # user ID
        ...     "email": "user@example.com",
        ...     "full_name": "John Doe"
        ... })
    """
    to_encode = data.copy()

    # Convert user_id to string if it's an integer
    if "user_id" in to_encode and isinstance(to_encode["user_id"], int):
        to_encode["user_id"] = str(to_encode["user_id"])

    expire = datetime.utcnow() + timedelta(minutes=SERVICE_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "type": "service",
        "iss": "platform",  # Issued by Platform
        "aud": "labeler"    # Intended for Labeler
    })

    # Use SERVICE_JWT_SECRET (separate from the auth service tokens)
    encoded_jwt = jwt.encode(to_encode, settings.SERVICE_JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def decode_service_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a service-to-service JWT token.

    Args:
        token: Service JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid, expired, or not a service token
    """
    try:
        payload = jwt.decode(
            token,
            settings.SERVICE_JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"verify_aud": False}  # Audience verification optional
        )

        # Verify token type
        if payload.get("type") != "service":
            raise JWTError("Not a service token")

        return payload
    except JWTError as e:
        raise JWTError(f"Invalid service token: {str(e)}")

