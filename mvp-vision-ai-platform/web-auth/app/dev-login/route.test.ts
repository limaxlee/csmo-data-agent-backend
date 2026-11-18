import { afterEach, describe, expect, it, vi } from "vitest"
import { NextRequest } from "next/server"
import { GET } from "./route"

vi.mock("../service-token", () => ({
  mintServiceToken: vi.fn(async () => ({ token: "test-token", expiresAt: 1234567890 })),
}))

afterEach(() => vi.unstubAllEnvs())

function enable() {
  vi.stubEnv("DEV_LOGIN_ENABLED", "true")
  vi.stubEnv("DEV_LOGIN_ALLOWED_IDS", "stage.admin")
  vi.stubEnv("DEV_LOGIN_ALLOW_ADMIN", "false")
  vi.stubEnv("AUTH_ALLOWED_CALLBACK_ORIGINS", "http://localhost:3391")
}

function request(callback: string, loginid = "stage.admin") {
  return new NextRequest(`http://localhost:3020/auth/dev-login?${new URLSearchParams({ loginid, role: "admin", redirect: callback })}`, {
    headers: { host: "localhost:3020" },
  })
}

describe("development login callback", () => {
  it("returns to an explicitly allowed Dashboard origin, preserving query/hash", async () => {
    enable()
    const callback = "http://localhost:3391/dashboard?tab=project#history"
    const response = await GET(request(callback))
    expect(response.status).toBe(307)
    expect(response.headers.get("location")).toBe(callback)
    expect(response.cookies.get("dice.dev-role")?.value).toBe("user")
    expect(response.cookies.get("dice.dev-loginid")?.httpOnly).toBe(true)
  })

  it("preserves same-origin callbacks and rejects unlisted origins", async () => {
    enable()
    expect((await GET(request("/platform?tab=project"))).headers.get("location"))
      .toBe("http://localhost:3020/platform?tab=project")
    for (const target of ["http://localhost:9999/dashboard", "https://untrusted.example/dashboard", "JAVA-SCRIPT:alert(1)"]) {
      expect((await GET(request(target))).headers.get("location")).toBe("http://localhost:3020/")
    }
  })

  it("keeps the route disabled without explicit activation and allowlist", async () => {
    enable()
    vi.stubEnv("DEV_LOGIN_ENABLED", "false")
    expect((await GET(request("/dashboard"))).status).toBe(404)
    vi.stubEnv("DEV_LOGIN_ENABLED", "true")
    vi.stubEnv("DEV_LOGIN_ALLOWED_IDS", "")
    expect((await GET(request("/dashboard"))).status).toBe(404)
  })

  it("rejects a user outside the allowlist", async () => {
    enable()
    expect((await GET(request("http://localhost:3391/dashboard", "unknown"))).status).toBe(403)
  })
})

