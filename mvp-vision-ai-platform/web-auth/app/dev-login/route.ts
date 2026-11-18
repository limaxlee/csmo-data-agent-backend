import { NextRequest, NextResponse } from "next/server"
import { mintServiceToken, type AdfsIdentity } from "../service-token"
import { authorizeDevLogin, readDevLoginConfig } from "./config"
import { isAllowedCallbackOrigin } from "../auth-origin"

export const dynamic = "force-dynamic"

function requestOrigin(request: NextRequest): string {
  const protocol = request.headers.get("x-forwarded-proto") || request.nextUrl.protocol.replace(":", "")
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host")
  return `${protocol}://${host}`
}

function safeRedirect(request: NextRequest, raw: string | null): URL | null {
  if (!raw) return null
  const origin = requestOrigin(request)
  try {
    const target = new URL(raw, origin)
    return target.origin === origin || isAllowedCallbackOrigin(target.origin)
      ? target
      : new URL("/", origin)
  } catch {
    return new URL("/", origin)
  }
}

// Runtime opt-in ADFS simulator. A non-empty login ID allowlist is mandatory.
export async function GET(request: NextRequest) {
  const config = readDevLoginConfig()
  if (!config.enabled) {
    return NextResponse.json({ error: "not_found" }, { status: 404 })
  }

  const { searchParams } = new URL(request.url)
  const authorized = authorizeDevLogin(
    searchParams.get("loginid"),
    searchParams.get("role"),
    config,
  )
  if (!authorized) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 })
  }

  const { loginId, role } = authorized
  const roles = role === "admin" ? ["admin"] : []

  const identity: AdfsIdentity = {
    loginid: loginId,
    email: `${loginId}@samsung.com`,
    fullName: loginId,
    department: null,
    company: null,
    uniqueName: null,
    sid: null,
    roles,
  }

  try {
    const minted = await mintServiceToken(identity)

    const redirectTarget = safeRedirect(request, searchParams.get("redirect"))
    const body = {
      accessToken: minted.token,
      tokenType: "Bearer",
      expiresAt: minted.expiresAt,
    }

    const response = redirectTarget
      ? NextResponse.redirect(redirectTarget)
      : NextResponse.json(body, { headers: { "Cache-Control": "no-store" } })

    // /token, /session 엔드포인트가 이 쿠키를 읽어 dev 세션으로 처리한다.
    const secure = requestOrigin(request).startsWith("https://")
    response.cookies.set("dice.dev-loginid", loginId, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      secure,
      maxAge: 60 * 60,
    })
    response.cookies.set("dice.dev-role", role, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      secure,
      maxAge: 60 * 60,
    })

    return response
  } catch (error) {
    console.error("[dev-login] failed to mint service token:", error)
    return NextResponse.json({ error: "token_mint_failed" }, { status: 500 })
  }
}

