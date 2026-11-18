import { NextRequest, NextResponse } from "next/server"
import { GET as getServiceToken } from "../token/route"

export const dynamic = "force-dynamic"

function result(isAdmin: boolean, status = 200, href?: string) {
  return NextResponse.json(
    { isAdmin, ...(isAdmin && href ? { href } : {}) },
    { status, headers: { "Cache-Control": "no-store" } },
  )
}

/** Menu visibility only; Dashboard and domain APIs authorize independently. */
export async function GET(request: NextRequest) {
  if (process.env.DASHBOARD_ENABLED === "false") return result(false)
  try {
    const tokenResponse = await getServiceToken(request)
    if (!tokenResponse.ok) return result(false, tokenResponse.status === 401 ? 401 : 503)
    const token = await tokenResponse.json()
    if (typeof token.accessToken !== "string" || !token.accessToken.trim()) return result(false, 503)

    const base = (process.env.USER_SERVICE_API_URL || "").trim().replace(/\/+$/, "")
    if (!base) return result(false, 503)
    const endpoint = new URL(`${base}/users/me`)
    if (!['http:', 'https:'].includes(endpoint.protocol) || endpoint.username || endpoint.password || endpoint.search || endpoint.hash) {
      return result(false, 503)
    }
    const response = await fetch(endpoint.href, {
      headers: { Authorization: `Bearer ${token.accessToken}` },
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(5_000),
    })
    if (response.status === 401) return result(false, 401)
    if (response.status === 403) return result(false)
    if (response.status !== 200) return result(false, 503)
    const profile = await response.json()
    if (!profile || typeof profile.id !== "string" || !profile.id.trim()
      || typeof profile.is_active !== "boolean" || typeof profile.system_role !== "string") {
      return result(false, 502)
    }
    if (!profile.is_active || profile.system_role !== "admin") return result(false)
    const href = (process.env.DASHBOARD_URL || "/dashboard").trim()
    const target = new URL(href, request.nextUrl.origin)
    if (!['http:', 'https:'].includes(target.protocol)) return result(false, 503)
    return result(true, 200, href)
  } catch {
    return result(false, 503)
  }
}
