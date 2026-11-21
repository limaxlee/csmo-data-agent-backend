"""
Service JWT Authentication

Hybrid JWT approach for microservice-to-microservice authentication.
Combines user context with service authentication for secure, auditable communication.

Architecture:
- Each service generates short-lived JWTs (5min default) for inter-service calls
- JWT contains: user_id (for permissions), service name (for audit), scopes (for authorization)
- Downstream services verify JWT and enforce user permissions

Usage:
    # Platform calling Labeler
    token = ServiceJWT.create_service_token(
        user_id=current_user.id,
        service_name="platform",
        scopes=["labeler:read", "labeler:write"]
    )

    # Background job (no user context)
    token = ServiceJWT.create_background_token(
        service_name="platform-training",
        scopes=["labeler:read"]
    )

    # Labeler verifying token
    payload = ServiceJWT.verify_token(token, required_scopes=["labeler:read"])
    user_id = payload["sub"]  # Extract user_id for permission checks

Reference: docs/cowork/MICROSERVICE_AUTHENTICATION_ANALYSIS.md
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import jwt
import logging
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class ServiceJWT:
    """
    Service JWT generator and validator for microservice authentication.

    This implements a hybrid authentication approach:
    - User context (user_id) for permission checks
    - Service identity (service name) for audit trail
    - Scopes for fine-grained authorization
    - Short-lived tokens (5min) for security
    """

    # Standard scopes for common operations
    SCOPES = {
        # Labeler service scopes
        "labeler:read": "Read dataset metadata and annotations",
        "labeler:write": "Create/update datasets and annotations",
        "labeler:delete": "Delete datasets",
        "labeler:admin": "Administrative operations on Labeler",

        # Training service scopes
        "training:execute": "Execute training jobs",
        "training:preflight": "Validate candidate training metadata without dispatch",
        "training:monitor": "Monitor training status",
        "training:cancel": "Cancel training jobs",

        # Model registry scopes
        "models:read": "Read model metadata",
        "models:write": "Upload/update models",
        "models:deploy": "Deploy models to inference",

        # Analytics scopes
        "analytics:read": "Read analytics data",
        "analytics:write": "Write analytics events",
    }

    @staticmethod
    def create_service_token(
        user_id: str,  # user ID
        service_name: str,
        scopes: List[str],
        expires_minutes: int = 5,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate service JWT for inter-service communication with user context.

        Args:
            user_id: ID of the user making the request (for permission checks)
            service_name: Name of the calling service (e.g., "platform", "labeler")
            scopes: List of scopes/permissions (e.g., ["labeler:read", "labeler:write"])
            expires_minutes: Token expiration time in minutes (default: 5)
            additional_claims: Optional additional claims to include in JWT

        Returns:
            JWT token string

        Example:
            >>> token = ServiceJWT.create_service_token(
            ...     user_id="550e8400-e29b-41d4-a716-446655440000",  # user ID
            ...     service_name="platform",
            ...     scopes=["labeler:read"]
            ... )
            >>> # Use token in Authorization header: Bearer {token}
        """
        now = datetime.utcnow()

        payload = {
            # Standard JWT claims
            "sub": str(user_id),  # Subject: user ID
            "iat": now,  # Issued at
            "exp": now + timedelta(minutes=expires_minutes),  # Expiration
            "nbf": now,  # Not before

            # Custom claims
            "service": service_name,  # Calling service
            "scopes": scopes,  # Permissions
            "type": "service",  # Token type
        }

        # Add additional claims if provided
        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, settings.SERVICE_JWT_SECRET, algorithm="HS256")

        logger.debug(
            f"[ServiceJWT] Generated token: service={service_name}, "
            f"user={user_id}, scopes={scopes}, expires={expires_minutes}m"
        )

        return token

    @staticmethod
    def create_background_token(
        service_name: str,
        scopes: List[str],
        expires_hours: int = 1,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate service JWT for background jobs (no user context).

        Use this for system operations that don't have a user context:
        - Scheduled jobs
        - Training jobs (after initial submission)
        - System maintenance tasks

        Args:
            service_name: Name of the service (e.g., "platform-training")
            scopes: List of scopes/permissions
            expires_hours: Token expiration time in hours (default: 1)
            additional_claims: Optional additional claims

        Returns:
            JWT token string

        Example:
            >>> token = ServiceJWT.create_background_token(
            ...     service_name="platform-training",
            ...     scopes=["labeler:read", "training:execute"],
            ...     expires_hours=24  # Long-running training job
            ... )
        """
        now = datetime.utcnow()

        payload = {
            # Standard JWT claims
            "sub": f"service:{service_name}",  # Service identity (must be a string for Labeler validation)
            "iat": now,
            "exp": now + timedelta(hours=expires_hours),
            "nbf": now,

            # Custom claims
            "service": service_name,
            "scopes": scopes,
            "type": "background",  # Background job token
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, settings.SERVICE_JWT_SECRET, algorithm="HS256")

        logger.debug(
            f"[ServiceJWT] Generated background token: service={service_name}, "
            f"scopes={scopes}, expires={expires_hours}h"
        )

        return token

    @staticmethod
    def verify_token(
        token: str,
        required_scopes: Optional[List[str]] = None,
        allowed_services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate service JWT and check scopes/service identity.

        Args:
            token: JWT token to validate
            required_scopes: Optional list of required scopes (AND logic)
            allowed_services: Optional list of allowed calling services

        Returns:
            JWT payload dict with keys: sub, service, scopes, type, iat, exp

        Raises:
            HTTPException(401): If token is invalid or expired
            HTTPException(403): If required scopes not present or service not allowed

        Example:
            >>> payload = ServiceJWT.verify_token(
            ...     token,
            ...     required_scopes=["labeler:read"],
            ...     allowed_services=["platform"]
            ... )
            >>> user_id = payload["sub"]  # user ID string
        """
        try:
            # Decode and verify JWT
            payload = jwt.decode(
                token,
                settings.SERVICE_JWT_SECRET,
                algorithms=["HS256"]
            )

            # Verify service identity if restricted
            if allowed_services:
                service = payload.get("service")
                if service not in allowed_services:
                    logger.warning(
                        f"[ServiceJWT] Unauthorized service: {service} "
                        f"(allowed: {allowed_services})"
                    )
                    raise HTTPException(
                        status_code=403,
                        detail=f"Service '{service}' not authorized for this endpoint"
                    )

            # Verify scopes if required
            if required_scopes:
                token_scopes = set(payload.get("scopes", []))
                required_set = set(required_scopes)

                if not required_set.issubset(token_scopes):
                    missing = required_set - token_scopes
                    logger.warning(
                        f"[ServiceJWT] Insufficient scopes. Required: {required_scopes}, "
                        f"Got: {list(token_scopes)}, Missing: {list(missing)}"
                    )
                    raise HTTPException(
                        status_code=403,
                        detail=f"Insufficient scope. Required: {list(missing)}"
                    )

            logger.debug(
                f"[ServiceJWT] Token verified: service={payload.get('service')}, "
                f"user={payload.get('sub')}, scopes={payload.get('scopes')}"
            )

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("[ServiceJWT] Token expired")
            raise HTTPException(
                status_code=401,
                detail="Service token expired"
            )

        except jwt.InvalidTokenError as e:
            logger.warning(f"[ServiceJWT] Invalid token: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid service token"
            )

    @staticmethod
    def decode_token_unsafe(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode JWT without verification (for debugging/logging only).

        WARNING: Do NOT use for authentication! This skips all security checks.

        Args:
            token: JWT token to decode

        Returns:
            JWT payload dict or None if decoding fails

        Example:
            >>> payload = ServiceJWT.decode_token_unsafe(token)
            >>> logger.info(f"Token claims: {payload}")
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["HS256"]
            )
        except Exception as e:
            logger.error(f"[ServiceJWT] Failed to decode token: {e}")
            return None

    @staticmethod
    def get_user_id_from_token(payload: Dict[str, Any]) -> Optional[str]:
        """
        Extract user ID from verified token payload.

        Args:
            payload: Verified JWT payload from verify_token()

        Returns:
            User ID as string (opaque), or None for background tokens

        Example:
            >>> payload = ServiceJWT.verify_token(token)
            >>> user_id = ServiceJWT.get_user_id_from_token(payload)
            >>> if user_id:
            ...     # Check user permissions
        """
        sub = payload.get("sub")
        if sub is None or (isinstance(sub, str) and sub.startswith("service:")):
            return None  # No user context for background tokens

        return str(sub)

    @staticmethod
    def validate_scopes(scopes: List[str]) -> bool:
        """
        Validate that all requested scopes are defined.

        Args:
            scopes: List of scope strings

        Returns:
            True if all scopes are valid

        Raises:
            ValueError: If any scope is not defined in SCOPES
        """
        undefined = [s for s in scopes if s not in ServiceJWT.SCOPES]
        if undefined:
            raise ValueError(f"Undefined scopes: {undefined}")
        return True


# Convenience function for FastAPI dependency injection
async def get_service_auth(
    token: str,
    required_scopes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    FastAPI dependency for service authentication.

    Usage:
        @router.get("/datasets")
        async def list_datasets(
            auth: dict = Depends(get_service_auth)
        ):
            user_id = auth.get("user_id")
            service = auth.get("service")
            # ... use user_id for permission checks
    """
    from fastapi import Header

    # Extract token from Authorization header
    # (In actual usage, use OAuth2PasswordBearer)
    payload = ServiceJWT.verify_token(token, required_scopes=required_scopes)

    return {
        "user_id": ServiceJWT.get_user_id_from_token(payload),
        "service": payload.get("service"),
        "scopes": payload.get("scopes", []),
        "type": payload.get("type"),
        "payload": payload  # Full payload for additional claims
    }

