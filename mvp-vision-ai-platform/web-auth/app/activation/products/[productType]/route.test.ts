import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { NextRequest } from "next/server"
import { requireActivationIdentity } from "../../../lib/activation/auth"
import { activationDb } from "../../../lib/activation/database"
import { ActivationError } from "../../../lib/activation/errors"
import { POST } from "./route"

vi.mock("../../../lib/activation/auth", () => ({ requireActivationIdentity: vi.fn() }))
vi.mock("../../../lib/activation/database", () => ({ activationDb: vi.fn() }))
vi.mock("../../../lib/activation/key-generator", () => ({ generateActivationKey: () => "issued-key" }))

const query = vi.fn(async (_sql: string, _values: unknown[]) => ({ rows: [] }))
const body = {
  login_id: "bot-user", samsung_id: "samsung", username: "User",
  department: "Department", detail: "Testing activation", location: "Office PC",
  device_key: "", version: "> v1.7.0", issuer: "forged-issuer",
}

function issue(authorization?: string, input: unknown = body, cookie?: string) {
  const headers = new Headers({ "content-type": "application/json" })
  if (authorization !== undefined) headers.set("authorization", authorization)
  if (cookie) headers.set("cookie", cookie)
  return POST(new NextRequest("http://localhost/activation/products/runner", {
    method: "POST", headers, body: JSON.stringify(input),
  }), { params: { productType: "runner" } })
}

beforeEach(() => {
  vi.stubEnv("DICE_BOT_ACTIVATION_TOKEN", "current-test-token")
  vi.stubEnv("DICE_BOT_ACTIVATION_TOKEN_PREVIOUS", "")
  vi.mocked(activationDb).mockReturnValue({ query } as unknown as ReturnType<typeof activationDb>)
  vi.mocked(requireActivationIdentity).mockResolvedValue({
    loginId: "web-user", systemRole: "user", username: "Web User", department: "Department",
  })
  vi.spyOn(console, "info").mockImplementation(() => {})
  vi.spyOn(console, "warn").mockImplementation(() => {})
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.restoreAllMocks()
  vi.clearAllMocks()
})

describe("activation issuance authentication", () => {
  it("accepts the bot token without session or user-service verification and forces the issuer", async () => {
    const response = await issue("Bearer current-test-token")
    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ activation_key: "issued-key" })
    expect(requireActivationIdentity).not.toHaveBeenCalled()
    expect(query.mock.calls[0][1][0]).toBe("bot-user")
    expect(query.mock.calls[0][1][10]).toBe("dice-bot")
    expect(console.info).toHaveBeenCalledWith("Activation authentication: accepted issuer=dice-bot")
  })

  it("supports the previous token only during an explicitly configured rotation", async () => {
    vi.stubEnv("DICE_BOT_ACTIVATION_TOKEN_PREVIOUS", "previous-test-token")
    expect((await issue("bearer previous-test-token")).status).toBe(200)
    vi.stubEnv("DICE_BOT_ACTIVATION_TOKEN_PREVIOUS", "")
    expect((await issue("Bearer previous-test-token")).status).toBe(401)
  })

  it.each(["Bearer wrong", "Bearer", "Basic current-test-token", "Bearer current-test-token extra", "Bearer current-test-toke"])(
    "rejects invalid authorization even with cookies: %s", async (authorization) => {
      expect((await issue(authorization, body, "dice.session-token=valid-session")).status).toBe(401)
      expect(requireActivationIdentity).not.toHaveBeenCalled()
      expect(query).not.toHaveBeenCalled()
    },
  )

  it("requires a current server token even when a previous token is configured", async () => {
    vi.stubEnv("DICE_BOT_ACTIVATION_TOKEN", " ")
    vi.stubEnv("DICE_BOT_ACTIVATION_TOKEN_PREVIOUS", "previous-test-token")
    expect((await issue("Bearer previous-test-token")).status).toBe(503)
    expect(requireActivationIdentity).not.toHaveBeenCalled()
    expect(query).not.toHaveBeenCalled()
  })

  it.each([undefined, null, "", "   ", 42])("requires a nonempty bot login_id: %s", async (login_id) => {
    expect((await issue("Bearer current-test-token", { ...body, login_id })).status).toBe(400)
    expect(query).not.toHaveBeenCalled()
  })

  it.each([null, [], "invalid"])("rejects a non-object bot body: %s", async (input) => {
    expect((await issue("Bearer current-test-token", input)).status).toBe(400)
    expect(query).not.toHaveBeenCalled()
  })

  it("uses the active web identity and forces dice-web without authorization", async () => {
    vi.stubEnv("DICE_BOT_ACTIVATION_TOKEN", "")
    expect((await issue()).status).toBe(200)
    expect(requireActivationIdentity).toHaveBeenCalledOnce()
    expect(query.mock.calls[0][1][0]).toBe("web-user")
    expect(query.mock.calls[0][1][10]).toBe("dice-web")
  })

  it.each([401, 403, 503])("preserves web identity rejection with status %s", async (status) => {
    vi.mocked(requireActivationIdentity).mockRejectedValue(new ActivationError(status, "101", "Rejected"))
    expect((await issue()).status).toBe(status)
    expect(query).not.toHaveBeenCalled()
  })
})

