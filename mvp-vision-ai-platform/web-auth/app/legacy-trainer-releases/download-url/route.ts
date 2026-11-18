import { NextRequest, NextResponse } from "next/server"
import { isNextResponse, requireReleaseRole } from "../../lib/releaseAuth"
import { clampExpiresIn, getBucket, headObject, loadJsonObject, presignGetUrl } from "../../lib/releaseS3"

const PREFIX = "legacy-trainer-releases"
const VARIANTS = ["cu117", "cu128"] as const
const DEFAULT_EXPIRES_IN = 3600

export async function POST(request: NextRequest) {
  const auth = await requireReleaseRole(request)
  if (isNextResponse(auth)) return auth

  let body: any
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 })
  }

  const variant = String(body?.variant || "")
  if (!VARIANTS.includes(variant as any)) {
    return NextResponse.json(
      { detail: `Unsupported legacy trainer release variant: ${variant}` },
      { status: 404 },
    )
  }

  const bucket = getBucket()
  const manifest = (await loadJsonObject(bucket, `${PREFIX}/latest/manifest.json`)) || {}
  const entries: any[] = Array.isArray(manifest.assets) ? manifest.assets : []
  const entry = entries.find((item) => String(item?.variant || "") === variant)
  const storageKey = String(entry?.storage_key || "")

  if (!storageKey || !(await headObject(bucket, storageKey))) {
    return NextResponse.json(
      { detail: `Legacy trainer release variant '${variant}' is not uploaded` },
      { status: 404 },
    )
  }

  const expiresIn = clampExpiresIn(body?.expiration_seconds, DEFAULT_EXPIRES_IN)
  const downloadUrl = await presignGetUrl(bucket, storageKey, expiresIn)

  return NextResponse.json(
    { storage_key: storageKey, download_url: downloadUrl, expires_in: expiresIn },
    { headers: { "Cache-Control": "no-store" } },
  )
}
