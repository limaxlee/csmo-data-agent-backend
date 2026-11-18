import { NextRequest, NextResponse } from "next/server"
import { getToken } from "next-auth/jwt"
import { corsPreflight, withCors } from "../auth-origin"
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
    const devIdentity = authorizeDevLogin(
      request.cookies.get("dice.dev-loginid")?.value,
      request.cookies.get("dice.dev-role")?.value,
    )
    if (devIdentity) {
      const { loginId: devLoginid, role: devRole } = devIdentity
      return withCors(
        request,
        NextResponse.json(
          {
            authenticated: true,
            user: { id: devLoginid, name: devLoginid, email: `${devLoginid}@samsung.com` },
            roles: devRole === "admin" ? ["admin"] : [],
            expiresAt: null,
          },
          { headers: { "Cache-Control": "no-store" } },
        ),
      )
    }

    return withCors(
      request,
      NextResponse.json(
        { authenticated: false, user: null, roles: [], error: token?.error ?? null },
        { headers: { "Cache-Control": "no-store" } },
      ),
    )
  }

  return withCors(
    request,
    NextResponse.json(
      {
        authenticated: true,
        user: {
          id: token.sub,
          name: token.name ?? null,
          email: token.email ?? null,
        },
        roles: token.roles ?? [],
        expiresAt: token.expiresAt ?? null,
      },
      { headers: { "Cache-Control": "no-store" } },
    ),
  )
}
