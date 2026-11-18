import { NextRequest, NextResponse } from "next/server"
import { isNextResponse, requireReleaseRole } from "../../../lib/releaseAuth"
import {
  clampExpiresIn,
  getBucket,
  headObject,
  loadJsonObject,
  presignGetUrl,
} from "../../../lib/releaseS3"

const PREFIX =
  process.env.RUNNER_RELEASE_PARTNER_STORAGE_PREFIX || "runner-releases/windows-partner"

const VARIANT = "dice-runner-partner"
const FIXED_FILENAME = "dice-runner-partner-windows-x86_64.msi"
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
  if (variant && ![VARIANT, ...["api", "directml", "cpu", "cuda", "tensorrt"].map((v) => `${VARIANT}-${v}`)].includes(variant)) {
    return NextResponse.json(
      { detail: `Unsupported partner runner variant: ${variant}` },
      { status: 404 },
    )
  }

  const bucket = getBucket()
  const prefix = PREFIX.replace(/^\/+|\/+$/g, "")
  const manifest = (await loadJsonObject(bucket, `${prefix}/latest/manifest.json`)) || {}
  const entries: any[] = Array.isArray(manifest.assets) ? manifest.assets : []
  const selected = variant || VARIANT
  const entry = entries.find((item) => String(item?.variant || "") === selected)
    || (selected === VARIANT ? entries.find((item) => item?.variant === `${VARIANT}-api`) : undefined)
    || {}
  if (selected !== VARIANT && !entry.storage_key) {
    return NextResponse.json({ detail: "Partner runner release is not uploaded yet" }, { status: 404 })
  }
  const storageKey = String(entry?.storage_key || `${prefix}/latest/${FIXED_FILENAME}`)
  const fileName = String(entry?.versioned_file_name || entry?.file_name || FIXED_FILENAME)

  if (!(await headObject(bucket, storageKey))) {
    return NextResponse.json(
      { detail: "Partner runner release is not uploaded yet" },
      { status: 404 },
    )
  }

  const expiresIn = clampExpiresIn(body?.expiration_seconds, DEFAULT_EXPIRES_IN)
  const downloadUrl = await presignGetUrl(bucket, storageKey, expiresIn)

  return NextResponse.json(
    { storage_key: storageKey, file_name: fileName, download_url: downloadUrl, expires_in: expiresIn },
    { headers: { "Cache-Control": "no-store" } },
  )
}

