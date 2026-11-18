import { SignJWT } from "jose"
import type { JWT } from "next-auth/jwt"

/**
 * ADFS id_token 클레임을 백엔드용 정규화 신원으로 변환하고,
 * SERVICE_JWT_SECRET 으로 서명한 service JWT 를 발급한다.
 *
 * 백엔드(platform/labeler)는 ADFS 를 직접 알 필요 없이 이 service JWT(iss=web-auth)만
 * 검증한다. loginid 를 subject/username 으로 사용해 기존 users.username
 * 과 매칭 → 기존 데이터(FK) 보존.
 */
export interface AdfsIdentity {
  loginid: string
  email: string | null
  fullName: string
  department: string | null
  company: string | null
  uniqueName: string | null
  sid: string | null
  roles: string[]
}

function decodeIdToken(idToken?: string): Record<string, any> {
  if (!idToken) return {}
  try {
    const payload = idToken.split(".")[1]
    return JSON.parse(Buffer.from(payload, "base64url").toString())
  } catch {
    return {}
  }
}

export function extractAdfsIdentity(token: JWT): AdfsIdentity {
  const claims = decodeIdToken(token.idToken)
  const upn: string | undefined = claims.upn

  // loginid 우선순위: loginid 클레임 > upn 로컬파트 > unique_name(CORP\\xxx)의 계정부 > sub
  const loginid =
    claims.loginid ||
    (upn ? String(upn).split("@")[0] : undefined) ||
    (claims.unique_name ? String(claims.unique_name).split("\\").pop() : undefined) ||
    claims.sub

  const groups = claims.groups || []
  const role = claims.role || []
  const roles = Array.from(
    new Set(
      [
        ...(Array.isArray(groups) ? groups : [groups]),
        ...(Array.isArray(role) ? role : [role]),
      ].filter(Boolean),
    ),
  ) as string[]

  return {
    loginid: String(loginid),
    email: upn ?? null,
    // ADFS id_token 에는 표시이름이 없어 upn/unique_name/loginid 순으로 대체
    fullName: upn || claims.unique_name || String(loginid),
    department: claims.deptname ?? null,
    company: claims.busname ?? null,
    uniqueName: claims.unique_name ?? null,
    sid: claims.sid ?? null,
    roles,
  }
}

const SERVICE_TOKEN_TTL_SECONDS = 3600 // ADFS access token 만료가 과거/부재일 때 기본 1시간

export interface MintedServiceToken {
  token: string
  expiresAt: number // 실제 service JWT 만료 (epoch seconds)
}

export async function mintServiceToken(
  identity: AdfsIdentity,
  expiresAt?: number,
): Promise<MintedServiceToken> {
  const secretValue = process.env.SERVICE_JWT_SECRET
  if (!secretValue) {
    throw new Error("SERVICE_JWT_SECRET is not configured")
  }
  const secret = new TextEncoder().encode(secretValue)

  // ADFS access token 만료에 맞추되, 없거나 이미 지난 값이면 now+TTL.
  // getToken 은 ADFS 토큰을 갱신하지 않으므로 expiresAt 이 과거일 수 있다 —
  // 이때 실제 발급 만료(now+TTL)를 반환해야 프론트가 잘못된(과거) 만료로
  // 매초 refresh 하는 것을 막는다.
  const now = Math.floor(Date.now() / 1000)
  const exp = expiresAt && expiresAt > now ? expiresAt : now + SERVICE_TOKEN_TTL_SECONDS

  // iat 를 exp 에서 역산해 결정론적으로 만든다. `setIssuedAt()` 을 인자 없이 쓰면
  // 매 요청 새 iat(초 단위) → 새 서명 → 새 토큰 문자열이 되고, 클라이언트의
  // `accessToken` 이 매번 새 값으로 갱신되어 그것에 의존하는 모든 effect 가
  // 재실행된다(예: 파일 선택창이 닫힐 때 발생하는 window focus → 재발급 →
  // 학습 페이지 추론 탭 리마운트). 동일 세션 + 동일 exp 면 동일 토큰이 나오도록
  // 고정한다 — 프로세스/replica 간에도 동일하므로 캐시가 필요 없다.
  // 백엔드 검증(platform/backend/app/core/web_auth.py)은 exp 만 확인하고 iat 는
  // 사용하지 않으므로 이 변경은 검증에 영향을 주지 않는다.
  const iat = exp - SERVICE_TOKEN_TTL_SECONDS

  const token = await new SignJWT({
    username: identity.loginid,
    email: identity.email,
    full_name: identity.fullName,
    department: identity.department,
    company: identity.company,
    unique_name: identity.uniqueName,
    sid: identity.sid,
    roles: identity.roles,
    type: "service",
  })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(identity.loginid)
    .setIssuer("web-auth")
    .setAudience("dice-backend")
    .setIssuedAt(iat)
    .setExpirationTime(exp)
    .sign(secret)

  return { token, expiresAt: exp }
}

