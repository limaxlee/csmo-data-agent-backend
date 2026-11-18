import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { NextRequest, NextResponse } from "next/server"
import { GET } from "./route"
import { GET as getServiceToken } from "../token/route"

vi.mock("../token/route", () => ({ GET: vi.fn() }))
const admin = { id: "canonical-id", system_role: "admin", is_active: true }
const fetcher = vi.fn()

beforeEach(() => {
  vi.stubEnv("USER_SERVICE_API_URL", "http://user.test/user/api/v1")
  vi.stubEnv("DASHBOARD_URL", "http://localhost:3391/dashboard")
  vi.stubGlobal("fetch", fetcher)
  fetcher.mockReset()
  vi.mocked(getServiceToken).mockImplementation(async () => NextResponse.json({ accessToken: "service-token" }))
})
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

const request = () => new NextRequest("http://localhost:3020/dashboard-access")

describe("admin-only Dashboard menu", () => {
  it("keeps the menu hidden until the Dashboard deployment is enabled", async () => {
    vi.stubEnv("DASHBOARD_ENABLED", "false")
    const response = await GET(request())
    expect(await response.json()).toEqual({ isAdmin: false })
    expect(response.headers.get("cache-control")).toBe("no-store")
    expect(getServiceToken).not.toHaveBeenCalled()
    expect(fetcher).not.toHaveBeenCalled()
  })

  it("uses the authoritative active admin profile and returns no token", async () => {
    fetcher.mockResolvedValue(Response.json(admin))
    const response = await GET(request())
    expect(await response.json()).toEqual({ isAdmin: true, href: "http://localhost:3391/dashboard" })
    expect(response.headers.get("cache-control")).toBe("no-store")
    expect(fetcher).toHaveBeenCalledWith("http://user.test/user/api/v1/users/me", expect.objectContaining({
      headers: { Authorization: "Bearer service-token" }, cache: "no-store", redirect: "error",
    }))
  })

  it("hides the menu for non-admin and inactive users", async () => {
    for (const profile of [{ ...admin, system_role: "member" }, { ...admin, system_role: "guest" }, { ...admin, is_active: false }]) {
      fetcher.mockResolvedValue(Response.json(profile))
      expect(await (await GET(request())).json()).toEqual({ isAdmin: false })
    }
  })

  it("does not contact user-service without a valid central session", async () => {
    vi.mocked(getServiceToken).mockResolvedValue(NextResponse.json({}, { status: 401 }))
    const response = await GET(request())
    expect(response.status).toBe(401)
    expect(await response.json()).toEqual({ isAdmin: false })
    expect(fetcher).not.toHaveBeenCalled()
  })

  it("fails closed for upstream auth errors and outages", async () => {
    for (const [upstream, expected] of [[401, 401], [403, 200], [500, 503], [302, 503]]) {
      fetcher.mockResolvedValue(new Response(null, { status: upstream }))
      const response = await GET(request())
      expect(response.status).toBe(expected)
      expect(await response.json()).toEqual({ isAdmin: false })
    }
    fetcher.mockRejectedValue(new Error("timeout"))
    expect((await GET(request())).status).toBe(503)
  })

  it("rejects malformed profiles and configuration", async () => {
    for (const profile of [{}, null, { ...admin, id: " " }, { ...admin, is_active: "true" }]) {
      fetcher.mockResolvedValue(Response.json(profile))
      expect((await GET(request())).status).toBe(502)
    }
    vi.stubEnv("USER_SERVICE_API_URL", "")
    expect((await GET(request())).status).toBe(503)
  })

  it("supports a same-origin production destination and rejects script destinations", async () => {
    fetcher.mockImplementation(async () => Response.json(admin))
    vi.stubEnv("DASHBOARD_URL", "")
    expect(await (await GET(request())).json()).toEqual({ isAdmin: true, href: "/dashboard" })
    vi.stubEnv("DASHBOARD_URL", "JAVA-SCRIPT:alert(1)")
    expect((await GET(request())).status).toBe(503)
  })
})
