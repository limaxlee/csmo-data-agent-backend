// Shared platform->storage-prefix resolution for the runner-envs routes
// (catalog listing + download-url). Both need to turn an optional
// ?platform=linux|windows query param into the actual runner-envs/<platform>
// prefix, swapping the trailing platform segment of RUNNER_ENV_STORAGE_PREFIX.

export const SUPPORTED_PLATFORMS = new Set(["linux", "windows"])
const CONFIGURED_PREFIX = process.env.RUNNER_ENV_STORAGE_PREFIX || "runner-envs/linux"

export function storagePrefix(platform: string | null): string {
  const configured = CONFIGURED_PREFIX.replace(/^\/+|\/+$/g, "")
  const value = (platform || "").trim().toLowerCase()
  if (!value) return configured
  if (!SUPPORTED_PLATFORMS.has(value)) {
    throw new Error(`platform must be one of: ${Array.from(SUPPORTED_PLATFORMS).sort().join(", ")}`)
  }
  const parts = configured.split("/")
  const last = parts[parts.length - 1]?.toLowerCase()
  const root = parts.length >= 2 && SUPPORTED_PLATFORMS.has(last) ? parts.slice(0, -1).join("/") : configured
  return `${root}/${value}`.replace(/^\/+/, "")
}
