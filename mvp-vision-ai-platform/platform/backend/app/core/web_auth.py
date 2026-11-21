"""web-auth Service JWT 검증 모듈.

ADFS 통합 이후 사용자 인증 흐름:
    브라우저 → web-auth(NextAuth/ADFS) → service JWT 발급(/token)
    → 프론트엔드가 Bearer 로 백엔드 호출 → 이 모듈이 검증

백엔드는 ADFS 를 직접 알지 않는다. web-auth 가 id_token 클레임을 정규화해
SERVICE_JWT_SECRET(HS256) 으로 서명한 JWT(iss="web-auth")만 검증한다.

토큰 페이로드 (web-auth/app/service-token.ts 와 1:1 대응):
    sub        : loginid (Samsung ID, 예: donghy.kim)
    username   : loginid
    email      : upn (donghy.kim@samsung.com)
    full_name  : 표시이름 (ADFS 미제공 시 upn/loginid)
    department : deptname
    company    : busname
    roles      : ADFS groups/role (없을 수 있음)
    sid, unique_name, type="service", iss="web-auth"
"""

from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings
from app.db.models import UserRole

WEB_AUTH_ISSUER = "web-auth"
ALGORITHM = "HS256"


class WebAuthPayload(BaseModel):
    """web-auth service JWT 페이로드."""

    sub: str  # loginid
    iss: str
    exp: int

    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    company: Optional[str] = None
    unique_name: Optional[str] = None
    sid: Optional[str] = None
    roles: list[str] = []
    type: Optional[str] = None

    class Config:
        extra = "ignore"

    @property
    def loginid(self) -> str:
        """매칭 키: username(loginid) 우선, 없으면 sub."""
        return (self.username or self.sub or "").strip()


def is_web_auth_token(token: str) -> bool:
    """검증 없이 iss 만 들여다봐 web-auth 토큰인지 판별 (라우팅용)."""
    try:
        claims = jwt.get_unverified_claims(token)
        return claims.get("iss") == WEB_AUTH_ISSUER
    except Exception:
        return False


def verify_web_auth_token(token: str) -> WebAuthPayload:
    """web-auth service JWT 검증.

    Args:
        token: Bearer 토큰 문자열

    Returns:
        WebAuthPayload: 검증된 페이로드

    Raises:
        JWTError: 서명/만료/issuer 검증 실패 시
    """
    try:
        payload = jwt.decode(
            token,
            settings.SERVICE_JWT_SECRET,
            algorithms=[ALGORITHM],
            options={
                "verify_aud": False,  # aud 는 강제하지 않음
                "verify_exp": True,
            },
        )
    except JWTError as e:
        raise JWTError(f"web-auth token validation failed: {str(e)}")

    if payload.get("iss") != WEB_AUTH_ISSUER:
        raise JWTError(f"Invalid issuer: expected '{WEB_AUTH_ISSUER}', got '{payload.get('iss')}'")

    return WebAuthPayload(**payload)


def map_web_auth_roles_to_system_role(roles: list[str]) -> Optional[UserRole]:
    """ADFS roles 를 시스템 역할로 매핑.

    ADFS 토큰에 role/group 클레임이 없으면 None 을 반환한다.
    호출부는 None 일 때 기존 사용자의 역할을 **유지**해야 한다 (강등 방지).
    신규 사용자에 한해 None → GUEST 로 처리.
    """
    normalized = {r.lower() for r in roles if r}
    if not normalized:
        return None

    if "admin" in normalized:
        return UserRole.ADMIN
    return UserRole.MEMBER
