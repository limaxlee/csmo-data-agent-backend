import { NextRequest, NextResponse } from "next/server"
import { isNextResponse, requireReleaseRole } from "../../lib/releaseAuth"
import { getBucket, headObject, loadJsonObject } from "../../lib/releaseS3"

const PREFIX = "legacy-trainer-releases"
const VARIANTS = ["cu117", "cu128"] as const

const DEFAULT_TITLES: Record<string, string> = {
  cu117: "DICE v2 Offline Trainer (CUDA 11.7)",
  cu128: "DICE v2 Offline Trainer (CUDA 12.8)",
}
const DEFAULT_DESCRIPTIONS: Record<string, string> = {
  cu117: "Full offline installer for the legacy DICE v2 trainer, bundled for CUDA 11.7 hosts.",
  cu128: "Full offline installer for the legacy DICE v2 trainer, bundled for CUDA 12.8 hosts.",
}

export async function GET(request: NextRequest) {
  const auth = await requireReleaseRole(request)
  if (isNextResponse(auth)) return auth

  const bucket = getBucket()
  const manifest = (await loadJsonObject(bucket, `${PREFIX}/latest/manifest.json`)) || {}
  const entries: any[] = Array.isArray(manifest.assets) ? manifest.assets : []

  const assets = []
  for (const entry of entries) {
    const variant = String(entry?.variant || "")
    if (!VARIANTS.includes(variant as any)) continue
    const storageKey = String(entry?.storage_key || "")
    if (!storageKey) continue

    const head = await headObject(bucket, storageKey)
    if (!head) continue

    assets.push({
      variant,
      title: String(entry.title || DEFAULT_TITLES[variant]),
      description: String(entry.description || DEFAULT_DESCRIPTIONS[variant]),
      file_name: String(entry.file_name || `${variant}.zip`),
      size_bytes: Number(head.ContentLength ?? entry.size_bytes ?? 0),
      sha256: String(entry.sha256 || "").toLowerCase(),
      updated_at: (head.LastModified || new Date()).toISOString(),
    })
  }
  assets.sort((a, b) => VARIANTS.indexOf(a.variant as any) - VARIANTS.indexOf(b.variant as any))

  return NextResponse.json(
    {
      version: String(manifest.version || "latest"),
      generated_at: String(manifest.generated_at || new Date().toISOString()),
      assets,
    },
    { headers: { "Cache-Control": "no-store" } },
  )
}

