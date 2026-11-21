"""Personal API token (PAT) helpers.

순수 함수만 — DB 의존 없음. platform/labeler 백엔드가 동일 로직을 공유하기 위해
양쪽에 같은 구현을 둔다 (별도 패키지 의존 없이 일관성 유지).

토큰 포맷: ``dice_pat_<urlsafe-random>``
- 평문은 발급 시 1회만 노출, 저장은 SHA-256 해시만.
- 표시용 prefix(``dice_pat_`` + 앞 6자)는 목록 UI 에서 식별용으로 사용.
"""

from __future__ import annotations

import hashlib
import secrets

TOKEN_PREFIX = "dice_pat_"
_DISPLAY_PREFIX_LEN = len(TOKEN_PREFIX) + 6


def is_api_token(token: str) -> bool:
    """Bearer 값이 PAT 인지 접두어로 판별 (라우팅용)."""
    return token.startswith(TOKEN_PREFIX)


def hash_api_token(token: str) -> str:
    """평문 토큰 → SHA-256 hex (조회/저장용)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_api_token() -> tuple[str, str, str]:
    """새 PAT 생성.

    Returns:
        (full_token, token_prefix, token_hash)
        full_token 은 1회만 노출되고 저장하지 않는다.
    """
    full_token = f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
    token_prefix = full_token[:_DISPLAY_PREFIX_LEN]
    return full_token, token_prefix, hash_api_token(full_token)


__all__ = ["TOKEN_PREFIX", "is_api_token", "hash_api_token", "generate_api_token"]
