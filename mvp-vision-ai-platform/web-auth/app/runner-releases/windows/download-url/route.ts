import { NextRequest, NextResponse } from "next/server"
import { isNextResponse, requireReleaseRole } from "../../../lib/releaseAuth"
import { clampExpiresIn, getBucket, headObject, loadJsonObject, presignGetUrl } from "../../../lib/releaseS3"

const PREFIX = process.env.RUNNER_RELEASE_STORAGE_PREFIX || "runner-releases/windows"
const VARIANTS = [
  "dice-runner",
  "dice-runner-api",
  "dice-runner-directml",
  "dice-runner-cpu",
  "dice-runner-cuda",
  "dice-runner-tensorrt",
  "cosmo",
  "env-ultralytics",
  "env-huggingface",
  "env-timm",
  "env-openmm",
  "env-vfm-v1",
  "env-cosmo",
]
const FIXED_FILENAMES: Record<string, string> = {
  "dice-runner": "dice-runner-windows-x86_64.msi",
  "dice-runner-api": "dice-runner-api-windows-x86_64.msi",
  "dice-runner-directml": "dice-runner-directml-windows-x86_64.msi",
  "dice-runner-cpu": "dice-runner-cpu-windows-x86_64.msi",
  "dice-runner-cuda": "dice-runner-cuda-windows-x86_64.msi",
  "dice-runner-tensorrt": "dice-runner-tensorrt-windows-x86_64.zip",
  cosmo: "dice-runner-windows-x86_64-cosmo.zip",
  "env-ultralytics": "dice-env-windows-x86_64-ultralytics.zip",
  "env-huggingface": "dice-env-windows-x86_64-huggingface.zip",
  "env-timm": "dice-env-windows-x86_64-timm.zip",
  "env-openmm": "dice-env-windows-x86_64-openmm.zip",
  "env-vfm-v1": "dice-env-windows-x86_64-vfm-v1.zip",
  "env-cosmo": "dice-env-windows-x86_64-cosmo.zip",
}
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
  if (!VARIANTS.includes(variant)) {
    return NextResponse.json(
      { detail: `Unsupported runner release variant: ${variant}` },
      { status: 404 },
    )
  }

  const bucket = getBucket()
  const prefix = PREFIX.replace(/^\/+|\/+$/g, "")
  const manifest = (await loadJsonObject(bucket, `${prefix}/latest/manifest.json`)) || {}
  const entries: any[] = Array.isArray(manifest.assets) ? manifest.assets : []
  const entry = entries.find((item) => String(item?.variant || "") === variant)
    || (variant === "dice-runner" ? entries.find((item) => item?.variant === "dice-runner-api") : undefined)
  const storageKey = String(entry?.storage_key || `${prefix}/latest/${FIXED_FILENAMES[variant]}`)
  const fileName = String(
    entry?.versioned_file_name || entry?.file_name || FIXED_FILENAMES[variant],
  )

  if (!(await headObject(bucket, storageKey))) {
    return NextResponse.json(
      { detail: `Runner release variant '${variant}' is not uploaded` },
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
