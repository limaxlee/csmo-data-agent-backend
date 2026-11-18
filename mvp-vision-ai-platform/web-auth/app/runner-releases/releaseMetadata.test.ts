import { beforeEach, describe, expect, it, vi } from "vitest"
import { NextRequest } from "next/server"

const storage = vi.hoisted(() => ({ loadJsonObject: vi.fn(), headObject: vi.fn(), presignGetUrl: vi.fn() }))
vi.mock("../lib/releaseS3", () => ({ getBucket: () => "test-bucket", clampExpiresIn: () => 3600, ...storage }))
vi.mock("../lib/releaseAuth", () => ({
  requireReleaseRole: async () => ({}),
  isNextResponse: () => false,
}))

import { GET as internalRelease } from "./windows/latest/route"
import { GET as partnerRelease } from "./windows-partner/latest/route"
import { POST as internalDownload } from "./windows/download-url/route"
import { POST as partnerDownload } from "./windows-partner/download-url/route"

describe.each([
  ["internal", internalRelease, "dice-runner"],
  ["partner", partnerRelease, "dice-runner-partner"],
] as const)("%s release identity", (_name, getRelease, variant) => {
  beforeEach(() => {
    storage.headObject.mockResolvedValue({ ContentLength: 100, LastModified: new Date("2026-10-12T00:00:00Z") })
  })

  it("keeps semantic, installer and release identities distinct", async () => {
    storage.loadJsonObject.mockResolvedValue({
      semantic_version: "3.0.0",
      windows_installer_version: "64.2.513",
      version: "20261012-7477efc7",
      assets: [{ variant, sha256: "a".repeat(64) }],
    })
    const response = await getRelease(new NextRequest("http://localhost/latest"))
    const body = await response.json()
    expect(body.semantic_version).toBe("3.0.0")
    expect(body.build_version).toBe("64.2.513")
    expect(body.version).toBe("20261012-7477efc7")
    expect(body.assets[0].sha256).toBe("a".repeat(64))
  })

  it("does not infer product or build versions from an old release identifier", async () => {
    storage.loadJsonObject.mockResolvedValue({ version: "20261012-7477efc7", assets: [{ variant }] })
    const response = await getRelease(new NextRequest("http://localhost/latest"))
    const body = await response.json()
    expect(body.semantic_version).toBe("")
    expect(body.build_version).toBe("")
  })

  it("lists all four runtime installers separately", async () => {
    const variants = ["api", "directml", "cpu", "cuda", "tensorrt"].map((runtime) => ({
      variant: `${variant}-${runtime}`,
      storage_key: `test/${runtime}`,
      title: runtime,
      file_name: `${runtime}.${runtime === "tensorrt" ? "zip" : "msi"}`,
    }))
    storage.loadJsonObject.mockResolvedValue({ assets: variants })
    const response = await getRelease(new NextRequest("http://localhost/latest"))
    const body = await response.json()
    expect(body.assets.map((asset: { variant: string }) => asset.variant)).toEqual(variants.map((asset) => asset.variant))
  })
})

describe.each([
  [internalDownload, "dice-runner"],
  [partnerDownload, "dice-runner-partner"],
] as const)("runtime installer downloads", (download, prefix) => {
  it("resolves the legacy API-only variant against a new manifest", async () => {
    storage.loadJsonObject.mockResolvedValue({ assets: [{ variant: `${prefix}-api`, storage_key: "test/api", file_name: "api.msi" }] })
    storage.headObject.mockResolvedValue({})
    storage.presignGetUrl.mockResolvedValue("https://example.test/file")
    const request = new NextRequest("http://localhost/download", { method: "POST", body: JSON.stringify({ variant: prefix }) })
    const result = await (await download(request)).json()
    expect(result.storage_key).toBe("test/api")
    expect(result.file_name).toBe("api.msi")
  })

  it.each(["api", "directml", "cpu", "cuda", "tensorrt"])("resolves the %s artifact from its own manifest entry", async (runtime) => {
    const variant = `${prefix}-${runtime}`
    storage.loadJsonObject.mockResolvedValue({ assets: [{ variant, storage_key: `test/${variant}`, file_name: `${variant}.msi` }] })
    storage.headObject.mockResolvedValue({})
    storage.presignGetUrl.mockResolvedValue("https://example.test/file")
    const request = new NextRequest("http://localhost/download", { method: "POST", body: JSON.stringify({ variant }) })
    const result = await (await download(request)).json()
    expect(result.storage_key).toBe(`test/${variant}`)
    expect(result.file_name).toBe(`${variant}.msi`)
  })
})
