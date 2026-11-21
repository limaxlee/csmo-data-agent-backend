"""PAT(개인 API 토큰) 스코프 — deny-by-default 허용목록.

PAT 는 외부 App 용 자격증명이므로, 대화형 사용자(web-auth service JWT)와 달리
"로그인 → 데이터셋 등록 → 학습 모델 조회/다운로드" 외부 시나리오에 필요한
엔드포인트에만 접근할 수 있다. 허용목록에 없는 (method, path) 조합은 403.

계층 구조:
- 게이트웨이 AuthorizationPolicy → Tier 0(내부 전용·무인증: /internal, /debug, /callback) 차단
- 이 모듈 → 인증은 되지만 PAT 가 사용자 전권을 갖던 Tier 1/2 표면을 좁힘 (admin/파괴적 거부)

웹 UI(web-auth service JWT)에는 적용되지 않는다 — PAT 토큰에만 해당.
"""

import re

from app.core.config import settings

# 라우트는 API_V1_PREFIX(예: /platform/api/v1) 아래에 마운트되며, dice-vs 가
# rewrite 없이 백엔드로 전달하므로 요청 경로도 이 prefix 를 포함한다.
# main.py 는 게이트웨이용 API_V1_PREFIX 와 기본 /api/v1 두 prefix 모두에
# 라우터를 마운트하므로(로컬 직접 접근), 허용목록도 두 prefix 를 모두 매칭한다.
_DEFAULT_PREFIX = "/api/v1"
_PREFIXES = {
    (settings.API_V1_PREFIX or _DEFAULT_PREFIX).rstrip("/"),
    _DEFAULT_PREFIX,
}
_P = "(?:" + "|".join(re.escape(p) for p in sorted(_PREFIXES)) + ")"

# (HTTP method, path 정규식). 외부 App 시나리오 화이트리스트.
_ALLOWLIST = [
    ("GET", rf"{_P}/training-evidence/jobs/\d+/(?:summary|logs|metrics|analysis-context|data-profile|metric-analysis|learning-overview|evaluations|references|comparison|dataset-images(?:/[A-Za-z0-9_.-]+(?:/content)?)?|evaluations/\d+/examples(?:/\d+(?:/content)?)?|inference-runs(?:/\d+/results(?:/\d+(?:/content)?)?)?)"),
    ("GET", rf"{_P}/auth/me"),                                   # 토큰/신원 확인
    ("GET", rf"{_P}/projects"),                                  # 프로젝트 목록
    ("GET", rf"{_P}/projects/\d+"),                              # 프로젝트 상세
    ("GET", rf"{_P}/projects/\d+/experiments"),                 # 실험(학습 잡) 목록
    ("GET", rf"{_P}/export/capabilities"),                       # export 포맷
    ("GET", rf"{_P}/export/training/\d+/checkpoint-options"),   # 체크포인트 옵션
    ("POST", rf"{_P}/export/jobs"),                              # export 잡 생성
    ("GET", rf"{_P}/export/jobs/\d+"),                          # export 잡 상태
    ("GET", rf"{_P}/export/\d+/download"),                      # 모델 다운로드 URL
    # Dashboard(관리 현황) 읽기 전용 — Dashboard MCP 서버가 admin PAT 로 호출한다.
    # 모든 /dashboard/* 라우트는 require_dashboard_access(admin 전용)로 이미 게이트되고,
    # 여기서는 GET(집계 조회)만 허용한다. confirm/ignore 등 PATCH 는 허용하지 않는다.
    ("GET", rf"{_P}/dashboard(?:/.*)?"),                         # dashboard 집계/조회
    # GPU 클러스터 리소스 현황(대시보드 Resource 탭) — Dashboard MCP 서버가 admin PAT 로
    # 호출한다. history/daily-history/gpu-consumption 은 엔드포인트 자체에서 이미
    # admin 전용으로 게이트되므로 여기서는 GET 만 허용한다.
    ("GET", rf"{_P}/training/cluster/resources(?:/.*)?"),        # 클러스터 GPU 리소스 현황
    # 채팅 기반 학습 관리(MCP 서버) — 자연어로 학습 라이프사이클을 구동하는
    # 외부 App 시나리오. 조회 → 학습 잡 생성 → 시작 → 상태 → 취소.
    ("GET", rf"{_P}/datasets/available"),                        # 학습 가능 데이터셋 목록
    ("GET", rf"{_P}/datasets/[^/]+/annotation-versions"),      # 어노테이션 버전 목록
    ("GET", rf"{_P}/models/list"),                               # 모델 목록
    ("GET", rf"{_P}/models/[^/]+/[^/]+"),                       # 모델 상세(framework/model)
    ("GET", rf"{_P}/chatbot/training-jobs"),                     # 최근 학습 잡 목록
    ("POST", rf"{_P}/training/jobs"),                            # 학습 잡 생성(pending)
    ("GET", rf"{_P}/training/jobs/\d+"),                        # 학습 잡 상태/진행
    ("POST", rf"{_P}/training/jobs/\d+/start"),                 # 학습 시작(GPU)
    ("POST", rf"{_P}/training/jobs/\d+/cancel"),                # 학습 취소
]

_COMPILED = [(method, re.compile(rf"^{pattern}/?$")) for method, pattern in _ALLOWLIST]


def is_pat_path_allowed(method: str, path: str) -> bool:
    """PAT 가 (method, path) 를 호출할 수 있는지 — 허용목록에 없으면 False(거부)."""
    requested = (method or "").upper()
    return any(requested == allowed and rx.match(path) for allowed, rx in _COMPILED)


__all__ = ["is_pat_path_allowed"]
