import { NextRequest, NextResponse } from "next/server"
import { getToken } from "next-auth/jwt"

// web-auth 세션 쿠키 (api/auth/[...nextauth]/route.ts 의 cookies 설정과 이름 일치)
const SESSION_COOKIES = [
  "dice.session-token",
  "dice.callback-url",
  "dice.csrf-token",
  "dice.dev-loginid",
  "dice.dev-role",
]

function appBaseUrlFromAuthUrl(authUrl: string): string {
  const normalized = authUrl.trim().replace(/\/+$/, "")
  if (normalized.endsWith("/api/auth")) {
    const appUrl = normalized.slice(0, -"/api/auth".length)
    return appUrl || new URL(normalized).origin
  }
  return normalized
}

export async function GET(request: NextRequest) {
  const requestOrigin =
    `${request.headers.get("x-forwarded-proto") || "http"}://${request.headers.get("x-forwarded-host") || request.headers.get("host")}`
  const nextAuthUrl = process.env.NEXTAUTH_URL
  const baseUrl = (nextAuthUrl ? appBaseUrlFromAuthUrl(nextAuthUrl) : "") || requestOrigin
  const platformBasePath = (process.env.NEXT_PUBLIC_PLATFORM_BASE_PATH || "/platform").trim()

  // ADFS end_session_endpoint = {issuer}/oauth2/logout (레거시 인증 잔재 제거)
  // 로컬/프로덕션 동일 코드로 동작. dev-login 세션은 NextAuth 토큰 자체가 없어
  // 아래 `token?.idToken` 조건에서 자연히 ADFS 분기를 타지 않는다.
  const adfsIssuer = (process.env.ADFS_ISSUER_INTERNAL || process.env.ADFS_ISSUER || "")
    .trim()
    .replace(/\/+$/, "")

  const token = await getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
    cookieName: "dice.session-token",
  })

  // 최종 리다이렉트 URL (로그아웃 완료 후 platform으로)
  // Query parameter에서 redirect URL을 받으면 그걸 우선 사용
  const redirectParam = request.nextUrl.searchParams.get("redirect")
  const platformUrl = (process.env.PLATFORM_URL || "").trim().replace(/\/+$/, "") || baseUrl
  const finalRedirectUrl = redirectParam || `${platformUrl}${platformBasePath}`

  // ADFS SSO 세션 종료로 redirect (id_token 이 있으면 id_token_hint 전달).
  // 모든 경우 logout-success를 거쳐서 브라우저 쿠키를 삭제한 후 최종 리다이렉트.
  let redirectTo: string
  const postLogout = `${baseUrl}/logout-success?redirect=${encodeURIComponent(finalRedirectUrl)}`

  if (adfsIssuer && token?.idToken) {
    // ADFS logout이 필요한 경우, ADFS로 보낸 후 logout-success로 돌아옴
    const params = new URLSearchParams({
      id_token_hint: token.idToken as string,
      post_logout_redirect_uri: postLogout,
    })
    redirectTo = `${adfsIssuer}/oauth2/logout?${params}`
  } else {
    // ADFS가 없거나 토큰이 없으면 logout-success로 직접 이동
    // (로컬 쿠키 삭제 후 최종 리다이렉트)
    redirectTo = postLogout
  }

  const response = NextResponse.redirect(redirectTo)

  // 로컬 NextAuth 세션 쿠키 제거. ADFS 만 로그아웃하고 로컬 쿠키를 남기면
  // 재방문 시 그대로 로그인 상태가 되므로 반드시 함께 삭제한다.
  const isProduction = process.env.NODE_ENV === "production"
  const cookiesToClear = new Set<string>(SESSION_COOKIES)

  // NextAuth 가 토큰 크기 초과로 쿠키를 청크 분할(chunking)한 경우를 처리 (예: dice.session-token.0)
  for (const cookie of request.cookies.getAll()) {
    if (SESSION_COOKIES.some((base) => cookie.name.startsWith(`${base}.`))) {
      cookiesToClear.add(cookie.name)
    }
  }

  for (const name of cookiesToClear) {
    response.cookies.set(name, "", {
      path: "/",
      maxAge: 0,
      secure: isProduction,
      sameSite: "lax"
    })
  }

  return response
}

