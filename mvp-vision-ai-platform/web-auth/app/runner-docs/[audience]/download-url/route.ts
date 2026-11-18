import { NextRequest, NextResponse } from "next/server"
import { isNextResponse, requireReleaseRole } from "../../../lib/releaseAuth"
import { clampExpiresIn, getBucket, headObject, presignGetUrl } from "../../../lib/releaseS3"

const PREFIXES = {
  internal: process.env.RUNNER_DOCS_INTERNAL_STORAGE_PREFIX || "runner-docs/internal",
  partner: process.env.RUNNER_DOCS_PARTNER_STORAGE_PREFIX || "runner-docs/partner",
} as const
const LANGUAGES = new Set(["ko", "en"])

export async function POST(
  request: NextRequest,
  context: { params: { audience: string } },
) {
  const auth = await requireReleaseRole(request)
  if (isNextResponse(auth)) return auth

  const { audience } = context.params
  if (audience !== "internal" && audience !== "partner") {
    return NextResponse.json({ detail: "Unsupported Runner docs audience" }, { status: 404 })
  }

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 })
  }
  const lang = (body as { lang?: unknown })?.lang
  if (typeof lang !== "string" || !LANGUAGES.has(lang)) {
    return NextResponse.json({ detail: "Unsupported language" }, { status: 400 })
  }

  const prefix = PREFIXES[audience].replace(/^\/+|\/+$/g, "")
  const fileName = `runner-manual-${audience}-${lang}.html`
  const storageKey = `${prefix}/latest/${fileName}`
  const bucket = getBucket()
  if (!(await headObject(bucket, storageKey))) {
    return NextResponse.json({ detail: "Runner manual is not published yet" }, { status: 404 })
  }

  const expiresIn = clampExpiresIn(
    typeof (body as { expiration_seconds?: unknown })?.expiration_seconds === "number"
      ? (body as { expiration_seconds: number }).expiration_seconds
      : undefined,
    3600,
  )
  const downloadUrl = await presignGetUrl(bucket, storageKey, expiresIn)
  return NextResponse.json(
    { storage_key: storageKey, file_name: fileName, download_url: downloadUrl, expires_in: expiresIn },
    { headers: { "Cache-Control": "no-store" } },
  )
}

