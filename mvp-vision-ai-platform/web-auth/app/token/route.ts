import { NextRequest, NextResponse } from "next/server"
import { getToken } from "next-auth/jwt"
import { corsPreflight, withCors } from "../auth-origin"
import { extractAdfsIdentity, mintServiceToken, type AdfsIdentity } from "../service-token"
import { authorizeDevLogin } from "../dev-login/config"

export async function OPTIONS(request: NextRequest) {
  return corsPreflight(request)
}

export async function GET(request: NextRequest) {
  const token = await getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
    cookieName: "dice.session-token",
  })

  if (!token || token.error === "RefreshAccessTokenError") {
    // Runtime dev login cookie is accepted only while the ID remains allowed.
    const devIdentity = authorizeDevLogin(
      request.cookies.get("dice.dev-loginid")?.value,
      request.cookies.get("dice.dev-role")?.value,
    )
    if (devIdentity) {
      const { loginId: devLoginid, role: devRole } = devIdentity
      const identity: AdfsIdentity = {
        loginid: devLoginid,
        email: `${devLoginid}@samsung.com`,
        fullName: devLoginid,
        department: null,
        company: null,
        uniqueName: null,
        sid: null,
        roles: devRole === "admin" ? ["admin"] : [],
      }
      try {
        const minted = await mintServiceToken(identity)
        return withCors(
          request,
          NextResponse.json(
            { accessToken: minted.token, tokenType: "Bearer", expiresAt: minted.expiresAt },
            { headers: { "Cache-Control": "no-store" } },
          ),
        )
      } catch (error) {
        console.error("[dev /token] failed to mint dev service token:", error)
      }
    }

    return withCors(
      request,
      NextResponse.json(
        { error: "unauthorized" },
        { status: 401, headers: { "Cache-Control": "no-store" } },
      ),
    )
  }

  // 백엔드(platform/labeler)에는 ADFS access token 대신 web-auth 가 서명한
  // service JWT 를 전달한다. 백엔드는 ADFS 를 모른 채 SERVICE_JWT_SECRET 으로 검증하고
  // loginid 로 기존 사용자를 매칭한다.
  try {
    const identity = extractAdfsIdentity(token)
    const minted = await mintServiceToken(identity, token.expiresAt as number | undefined)

    return withCors(
      request,
      NextResponse.json(
        {
          accessToken: minted.token,
          tokenType: "Bearer",
          // 실제 service JWT 만료를 반환 (원본 ADFS expiresAt 은 과거일 수 있어 매초 refresh 유발)
          expiresAt: minted.expiresAt,
        },
        { headers: { "Cache-Control": "no-store" } },
      ),
    )
  } catch (error) {
    console.error("Failed to mint service token:", error)
    return withCors(
      request,
      NextResponse.json(
        { error: "service_token_error" },
        { status: 500, headers: { "Cache-Control": "no-store" } },
      ),
    )
  }
}
