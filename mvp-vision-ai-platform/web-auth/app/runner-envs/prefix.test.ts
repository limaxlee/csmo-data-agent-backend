import { afterEach, describe, expect, it, vi } from "vitest"

// storagePrefix reads RUNNER_ENV_STORAGE_PREFIX once at module load, so each
// scenario that needs a different configured prefix resets the module cache
// and re-imports after setting the env var.
async function loadWithPrefix(configuredPrefix: string) {
  vi.resetModules()
  process.env.RUNNER_ENV_STORAGE_PREFIX = configuredPrefix
  return await import("./prefix")
}

describe("storagePrefix", () => {
  afterEach(() => {
    delete process.env.RUNNER_ENV_STORAGE_PREFIX
  })

  it("preserves the default prefix when no platform is given", async () => {
    const { storagePrefix } = await loadWithPrefix("runner-envs/linux")
    expect(storagePrefix(null)).toBe("runner-envs/linux")
  })

  it("swaps the trailing platform segment", async () => {
    const { storagePrefix } = await loadWithPrefix("runner-envs/linux")
    expect(storagePrefix("windows")).toBe("runner-envs/windows")
    expect(storagePrefix("linux")).toBe("runner-envs/linux")
  })

  it("is case-insensitive on the platform param", async () => {
    const { storagePrefix } = await loadWithPrefix("runner-envs/linux")
    expect(storagePrefix("WINDOWS")).toBe("runner-envs/windows")
  })

  it("keeps a custom root when swapping platform", async () => {
    const { storagePrefix } = await loadWithPrefix("custom/envs/linux")
    expect(storagePrefix("windows")).toBe("custom/envs/windows")
  })

  it("rejects an unsupported platform", async () => {
    const { storagePrefix } = await loadWithPrefix("runner-envs/linux")
    expect(() => storagePrefix("darwin")).toThrow()
  })
})

