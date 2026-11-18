import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

/**
 * ADFS v4.0 Redirect URL 제약 해결을 위한 Middleware
 *
 * ADFS 에 "/" 경로만 등록 가능한 경우 활성화하면 됨:
 * 1. 사용자가 ADFS 로그인 완료
 * 2. ADFS 가 `/?code=xxx&state=yyy` 로 리다이렉트
 * 3. Middleware 가 /api/auth/callback/adfs?code=xxx&state=yyy 로 전달
 *
 * 현재 구성: ADFS 에 /api/auth/callback/adfs 가 직접 등록되어 있으므로
 * redirect 없이 NextResponse.next() 만 반환
 */
export function middleware(request: NextRequest) {
  // ADFS 가 "/" 만 redirect_uri 로 허용하는 경우 아래 주석 해제
  // const { pathname, search } = request.nextUrl
  // if (pathname === "/") {
  //   const code = request.nextUrl.searchParams.get("code")
  //   const error = request.nextUrl.searchParams.get("error")
  //   if (code || error) {
  //     return NextResponse.redirect(
  //       new URL(`/api/auth/callback/adfs${search}`, request.url)
  //     )
  //   }
  // }
  return NextResponse.next()
}

export const config = {
  matcher: [],
}

