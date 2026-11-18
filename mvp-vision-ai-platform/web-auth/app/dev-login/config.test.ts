import { describe, expect, it } from "vitest"
import { authorizeDevLogin, readDevLoginConfig } from "./config"

describe("runtime dev login configuration", () => {
  it("is disabled by default and when an allowlist is missing", () => {
    expect(readDevLoginConfig({}).enabled).toBe(false)
    expect(readDevLoginConfig({ DEV_LOGIN_ENABLED: "true" }).enabled).toBe(false)
  })

  it("normalizes an explicit allowlist", () => {
    const config = readDevLoginConfig({
      DEV_LOGIN_ENABLED: " TRUE ",
      DEV_LOGIN_ALLOWED_IDS: " Alice.Kim, bob.lee , ",
    })

    expect(config.enabled).toBe(true)
    expect([...config.allowedLoginIds]).toEqual(["alice.kim", "bob.lee"])
  })

  it("rejects users outside the allowlist", () => {
    const config = readDevLoginConfig({
      DEV_LOGIN_ENABLED: "true",
      DEV_LOGIN_ALLOWED_IDS: "alice.kim",
    })

    expect(authorizeDevLogin("mallory", "user", config)).toBeNull()
  })

  it("does not grant admin unless separately enabled", () => {
    const env = { DEV_LOGIN_ENABLED: "true", DEV_LOGIN_ALLOWED_IDS: "alice.kim" }
    const userOnly = readDevLoginConfig(env)
    expect(authorizeDevLogin(" Alice.Kim ", "admin", userOnly)).toEqual({
      loginId: "alice.kim",
      role: "user",
    })

    const admin = readDevLoginConfig({ ...env, DEV_LOGIN_ALLOW_ADMIN: "true" })
    expect(authorizeDevLogin("alice.kim", "admin", admin)).toEqual({
      loginId: "alice.kim",
      role: "admin",
    })
  })
})
