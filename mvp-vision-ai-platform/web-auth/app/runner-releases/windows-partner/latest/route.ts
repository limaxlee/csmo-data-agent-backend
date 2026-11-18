import { NextRequest, NextResponse } from "next/server"
import { isNextResponse, requireReleaseRole } from "../../../lib/releaseAuth"
import { getBucket, headObject, loadJsonObject } from "../../../lib/releaseS3"

const PREFIX =
  process.env.RUNNER_RELEASE_PARTNER_STORAGE_PREFIX || "runner-releases/windows-partner"

const VARIANT = "dice-runner-partner"
const FIXED_FILENAME = "dice-runner-partner-windows-x86_64.msi"

export async function GET(request: NextRequest) {
  const auth = await requireReleaseRole(request)
  if (isNextResponse(auth)) return auth

  const bucket = getBucket()
  const prefix = PREFIX.replace(/^\/+|\/+$/g, "")
  const manifest = (await loadJsonObject(bucket, `${prefix}/latest/manifest.json`)) || {}
  const entries: any[] = Array.isArray(manifest.assets) ? manifest.assets : []
  const supported = new Set([VARIANT, ...["api", "directml", "cpu", "cuda", "tensorrt"].map((v) => `${VARIANT}-${v}`)])
  const selected = entries.filter((entry) => supported.has(String(entry?.variant || "")))
  if (!selected.length) selected.push({ variant: VARIANT })
  const assets = []
  for (const entry of selected) {
    const variant = String(entry.variant)
    const storageKey = String(entry.storage_key || `${prefix}/latest/${FIXED_FILENAME}`)
    const head = await headObject(bucket, storageKey)
    if (head) assets.push({
          platform: "windows",
          variant,
          title: String(entry.title || "DICE Runner (Partner)"),
          description: String(
            entry.description ||
              "Partner build — requires a Sentinel HASP dongle to operate. Installs the DICE runner as a Windows service plus the desktop tray.",
          ),
          file_name: String(entry.versioned_file_name || entry.file_name || FIXED_FILENAME),
          size_bytes: Number(head.ContentLength ?? entry.size_bytes ?? 0),
          sha256: String(entry.sha256 || "").toLowerCase(),
          updated_at: (head.LastModified || new Date()).toISOString(),
          storage_key: storageKey,
        })
  }

  return NextResponse.json(
    {
      version: String(manifest.version || process.env.RUNNER_RELEASE_VERSION || "latest"),
      semantic_version: String(manifest.semantic_version || ""),
      build_version: String(manifest.windows_installer_version || ""),
      platform: "windows",
      generated_at: String(manifest.generated_at || new Date().toISOString()),
      assets,
    },
    { headers: { "Cache-Control": "no-store" } },
  )
}
